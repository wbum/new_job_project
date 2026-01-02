from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from workflow_service.app.database import get_db
from workflow_service.app.models.record import Record, StatusEnum
from workflow_service.app.schemas.record import RecordCreate, RecordResponse, RecordDetail
from workflow_service.app.services.processing import process_record

router = APIRouter()

@router.post("/records", response_model=RecordResponse, status_code=201)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rec = Record(payload=payload.dict(), status=StatusEnum.pending.value)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    background_tasks.add_task(process_record, db, rec.id)
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

@router.get("/reports/summary")
def get_summary(db: Session = Depends(get_db)):
    total = db.query(Record).count()
    processed = db.query(Record).filter(Record.status == StatusEnum.processed.value).count()
    failed = db.query(Record).filter(Record.status == StatusEnum.failed.value).count()
    # counts by classification
    counts = {}
    for cls in ["high", "medium", "low"]:
        counts[cls] = db.query(Record).filter(Record.classification == cls).count()
    avg_score = db.query(Record).filter(Record.score != None).with_entities(func.avg(Record.score)).scalar()
    return {
        "total": total,
        "processed": processed,
        "failed": failed,
        "by_classification": counts,
        "avg_score": float(avg_score) if avg_score is not None else None,
    }
