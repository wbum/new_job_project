import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.record import Record, StatusEnum

logger = logging.getLogger(__name__)


def process_record(record_id: str) -> None:
    """
    Background worker for processing a record.
    This function creates and closes its own DB session so it doesn't rely on the
    request-scoped session.
    """
    session: Optional[Session] = None
    try:
        session = SessionLocal()
        rec = session.query(Record).filter(Record.id == record_id).first()
        if not rec:
            logger.error("process_record: record %s not found", record_id)
            return

        # ---- Dummy processing logic ----
        # Replace with real processing: classification, scoring, etc.
        rec.classification = "low"
        rec.score = 0.0
        rec.status = StatusEnum.processed.value
        # --------------------------------

        session.commit()
        logger.info("process_record: record %s processed", record_id)
    except Exception:
        # Mark failed and persist error message
        logger.exception("process_record: unexpected error processing record %s", record_id)
        if session:
            try:
                # attempt to update record to failed
                rec = session.query(Record).filter(Record.id == record_id).first()
                if rec:
                    rec.status = StatusEnum.failed.value
                    rec.error = "processing error (see logs)"
                    session.commit()
            except Exception:
                session.rollback()
    finally:
        if session:
            session.close()
