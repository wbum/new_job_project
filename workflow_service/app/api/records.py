from typing import Optional
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..models.record import Record, StatusEnum
from ..schemas.record import RecordCreate, RecordResponse, RecordDetail
from ..services.processing import process_record
from ..services.reporting import get_records, ALLOWED_STATUSES


router = APIRouter()

@router.post("/records", response_model=RecordResponse, status_code=201)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rec = Record(
        source=payload.source,
        category=payload.category,
        payload=payload.payload,
        status=StatusEnum.pending.value,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    # Do NOT pass the request-scoped db session to the background task.
    # Pass only the record id and let the background worker open its own session.
    background_tasks.add_task(process_record, rec.id)
    return {"id": rec.id, "status": rec.status}

@router.get("/records/{record_id}", response_model=RecordDetail)
def get_record(record_id: str, db: Session = Depends(get_db)):
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    return {
        "id": rec.id,
        "payload": rec.payload,
        "status": rec.status,
        "classification": rec.classification,
        "score": rec.score,
        "error": rec.error,
    }


def _to_read_model(rec: Record) -> dict:
    """Convert a Record ORM object to a dictionary for the list endpoint."""
    # Decode JSON fields if they are strings
    payload_data = rec.payload
    if isinstance(payload_data, str):
        try:
            payload_data = json.loads(payload_data)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return {
        "id": rec.id,
        "created_at": rec.created_at.isoformat() + "Z" if rec.created_at else None,
        "status": rec.status,
        "source": rec.source,
        "category": rec.category,
        "payload": payload_data,
        "classification": rec.classification,
        "score": rec.score,
        "error": rec.error
    }


@router.get("/records")
def list_records(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    created_after: Optional[str] = Query(None, description="Filter by created after (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter by created before (ISO format)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    List records with optional filters and pagination.
    
    Returns a list of records matching the filters with pagination support.
    """
    # Validate status if provided
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {', '.join(ALLOWED_STATUSES)}"
        )
    
    # Parse dates
    from datetime import datetime
    parsed_created_after = None
    parsed_created_before = None
    
    if created_after:
        try:
            parsed_created_after = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid created_after format. Use ISO format.")
    
    if created_before:
        try:
            parsed_created_before = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid created_before format. Use ISO format.")
    
    # Call service layer
    items, total = get_records(
        db,
        status=status,
        category=category,
        created_after=parsed_created_after,
        created_before=parsed_created_before,
        limit=limit,
        offset=offset
    )
    
    # Convert items to response model
    items_data = [_to_read_model(rec) for rec in items]
    
    return {
        "items": items_data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/records/{record_id}/process", response_model=RecordResponse)
def trigger_process(record_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Manually trigger processing for a specific record.
    
    This endpoint is useful for testing and for reprocessing failed records.
    """
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Trigger background processing
    background_tasks.add_task(process_record, record_id)
    
    return {"id": rec.id, "status": rec.status}

