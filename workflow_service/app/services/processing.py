from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.record import Record

logger = logging.getLogger(__name__)


def compute_result_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a numeric score and classification from payload.

    Rules:
    - Look for numeric fields: priority, impact, urgency
    - score = sum of numeric values (missing => 0)
    - classification:
        score >= 12 -> "high"
        score >= 6  -> "medium"
        else -> "low"

    Returns a dict like {"score": 7.0, "classification": "medium"}.
    """
    def to_number(v: Any) -> float:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        # attempt to coerce numeric strings; raise ValueError on failure
        return float(v)

    priority = to_number(payload.get("priority"))
    impact = to_number(payload.get("impact"))
    urgency = to_number(payload.get("urgency"))

    score = priority + impact + urgency
    if score >= 12:
        classification = "high"
    elif score >= 6:
        classification = "medium"
    else:
        classification = "low"

    return {"score": score, "classification": classification}


def process_record(record_id: str) -> None:
    """
    Process a record by id. Uses its own DB session and persists changes.

    Behavior:
    - If record not found: log and return.
    - If record.status != "pending": no-op.
    - On success: set status "processed", write result JSON to record.result,
      set classification & score, commit.
    - On failure: set status "failed", write error info into record.result.error,
      commit (or rollback if commit itself fails).
    """
    session: Optional[Session] = None
    try:
        session = SessionLocal()
        rec = session.query(Record).filter(Record.id == record_id).first()
        if not rec:
            logger.error("process_record: record %s not found", record_id)
            return

        if rec.status != "pending":
            logger.info("process_record: record %s status is %s (skip)", record_id, rec.status)
            return

        # payload stored as JSON string in rec.payload
        payload = {}
        try:
            payload = json.loads(rec.payload)
        except Exception:
            # If payload cannot be parsed, treat as error
            raise ValueError("invalid payload JSON")

        # Compute result (may raise ValueError if numeric coercion fails)
        result = compute_result_from_payload(payload)

        # Persist derived fields
        rec.score = float(result.get("score", 0.0))
        rec.classification = result.get("classification")
        rec.result = json.dumps(result)
        rec.status = "processed"

        session.commit()
        logger.info("process_record: record %s processed", record_id)
    except Exception as exc:
        logger.exception("process_record: error processing record %s", record_id)
        # mark failed
        if session:
            try:
                rec = session.query(Record).filter(Record.id == record_id).first()
                if rec:
                    rec.status = "failed"
                    rec.error = str(exc)
                    # Also store an error result JSON for visibility
                    rec.result = json.dumps({"error": str(exc)})
                    session.commit()
            except Exception:
                session.rollback()
    finally:
        if session:
            session.close()
