from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.record import Record
from app.schemas.record import RecordCreate, RecordRead

router = APIRouter()


@router.post("/records", response_model=RecordRead, status_code=201)
def create_record(record_input: RecordCreate, db: Session = Depends(get_db)):
    """Create a new record with the provided source, category, and payload."""
    try:
        # Create new record
        new_record = Record(
            source=record_input.source,
            category=record_input.category,
            payload=record_input.payload,
            status='pending'
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while creating the record")
