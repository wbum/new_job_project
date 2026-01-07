from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.record import Record
from ..schemas.record import RecordCreate, RecordRead
from ..services import processing, reporting
from ..exceptions import NotFoundError, ConflictError

router = APIRouter()


def _fetch_record(db: Session, record_id: str) -> Record:
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise NotFoundError(message="record not found")
    return rec


def _to_read_model(rec: Record) -> RecordRead:
    payload = {}
    try:
        payload = json.loads(getattr(rec, "payload", "{}"))
    except Exception:
        payload = {}

    result = None
    raw_result = getattr(rec, "result", None)
    if raw_result:
        try:
            result = json.loads(raw_result)
        except Exception:
            result = None

    # use getattr for optional fields so missing attributes don't raise
    classification = getattr(rec, "classification", None)
    score = getattr(rec, "score", None)
    error = getattr(rec, "error", None)

    # ensure created_at is present (some model versions may use created_at or created)
    created_at = getattr(rec, "created_at", None)

    return RecordRead(
        id=rec.id,
        created_at=created_at,
        status=rec.status,
        source=rec.source,
        category=rec.category,
        payload=payload,
        result=result,
        classification=classification,
        score=score,
        error=error,
    )


@router.post("/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rec = Record(
        source=payload.source,
        category=payload.category,
        payload=json.dumps(payload.payload),
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Do not auto-process here (explicit trigger endpoint exists)
    return _to_read_model(rec)


def _parse_iso_datetime_optional(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid datetime: {value}")


@router.get("/records", response_model=dict)
def list_records(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List records with filters and pagination.
    - status, category (optional)
    - created_after, created_before (ISO date/time)
    - limit (default 50, max 200), offset (default 0)
    Returns: { items: [...], count: <page_count>, total: <total_matching> }
    """
    # enforce max limit
    if limit > 200:
        limit = 200

    # parse datetimes
    dt_after = _parse_iso_datetime_optional(created_after)
    dt_before = _parse_iso_datetime_optional(created_before)

    # fetch via service layer
    items, total = reporting.get_records(
        db,
        status=status,
        category=category,
        created_after=dt_after,
        created_before=dt_before,
        limit=limit,
        offset=offset,
    )

    return {"items": [_to_read_model(i) for i in items], "count": len(items), "total": total}


@router.get("/records/{record_id}", response_model=RecordRead)
def get_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)
    return _to_read_model(rec)


@router.post("/records/{record_id}/process", response_model=RecordRead)
def post_process_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)

    if rec.status != "pending":
        raise ConflictError(message="record is not pending", code="ALREADY_PROCESSED")

    # Run processing synchronously (service takes care of sessions & persistence)
    processing.process_record(rec.id)

    # Refresh record from DB to return updated state
    rec = db.query(Record).filter(Record.id == record_id).first()
    return _to_read_model(rec)
