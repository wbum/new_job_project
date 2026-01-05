import logging
import json
from typing import Optional

from sqlalchemy.orm import sessionmaker, Session

from ..database import engine
from ..models.record import Record, StatusEnum

# Create a session factory bound to the app's engine.
SessionLocal = sessionmaker(bind=engine)

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

        # Attempt to load payload safely (support JSON-string or already-parsed dict)
        payload = {}
        try:
            if isinstance(rec.payload, (str, bytes)):
                payload = json.loads(rec.payload)
            else:
                payload = rec.payload or {}
        except Exception:
            logger.exception("process_record: invalid payload for record %s", record_id)
            rec.status = StatusEnum.failed.value
            rec.error = "invalid payload"
            session.commit()
            return

        # Simple validation rule used by tests: if `priority` exists it must be numeric
        if "priority" in payload:
            try:
                # allow numeric strings that parse to float
                float(payload["priority"])
            except Exception:
                logger.info("process_record: invalid priority for record %s", record_id)
                rec.status = StatusEnum.failed.value
                rec.error = "invalid priority"
                session.commit()
                return

        # ---- Dummy processing logic (success) ----
        rec.classification = "low"
        rec.score = 0.0
        rec.status = StatusEnum.processed.value
        # ------------------------------------------

        session.commit()
        logger.info("process_record: record %s processed", record_id)
    except Exception:
        # Mark failed and persist error message
        logger.exception("process_record: unexpected error processing record %s", record_id)
        if session:
            try:
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