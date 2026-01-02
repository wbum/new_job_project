from __future__ import annotations

import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.record import Record
from ..schemas.record import RecordCreate, RecordRead
from ..services import processing

router = APIRouter()


def _fetch_record(db: Session, record_id: str) -> Record:
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")
    return rec


def _to_read_model(rec: Record) -> RecordRead:
    payload = {}
    try:
        payload = json.loads(rec.payload)
    except Exception:
        payload = {}

    result = None
    if rec.result:
        try:
            result = json.loads(rec.result)
        except Exception:
            result = None

    return RecordRead(
        id=rec.id,
        created_at=rec.created_at,
        status=rec.status,
        source=rec.source,
        category=rec.category,
        payload=payload,
        result=result,
        classification=rec.classification,
        score=rec.score,
        error=rec.error,
    )


@router.post("/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # create Record (persist payload as JSON string)
    rec = Record(
        source=payload.source,
        category=payload.category,
        payload=json.dumps(payload.payload),
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # (We previously scheduled background processing here in Day 3; keep or remove depending on Day 4)
    # background_tasks.add_task(processing.process_record, rec.id)

    return _to_read_model(rec)


@router.get("/records/{record_id}", response_model=RecordRead)
def get_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)
    return _to_read_model(rec)


@router.post("/records/{record_id}/process", response_model=RecordRead)
def post_process_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)

    if rec.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="record is not pending")

    # Run processing synchronously (service takes care of sessions & persistence)
    processing.process_record(rec.id)

    # Refresh record from DB to return updated state
    rec = db.query(Record).filter(Record.id == record_id).first()
    return _to_read_model(rec)
