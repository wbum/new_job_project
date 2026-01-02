from sqlalchemy.orm import Session
from workflow_service.app.models.record import Record, StatusEnum

def compute_score(metrics: dict) -> float:
    # Simple deterministic weighted sum; weights are a simple heuristic
    # If expected keys missing, default to 0
    severity = float(metrics.get("severity", 0))
    impact = float(metrics.get("impact", 0))
    urgency = float(metrics.get("urgency", 0))
    # weights: severity 0.5, impact 0.3, urgency 0.2
    score = severity * 0.5 + impact * 0.3 + urgency * 0.2
    return round(score, 2)

def classify(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"

def process_record(db: Session, record_id: str) -> None:
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        return
    try:
        record.status = StatusEnum.pending.value
        db.add(record)
        db.commit()
        # compute
        payload = record.payload or {}
        metrics = payload.get("metrics", {})
        score = compute_score(metrics)
        classification = classify(score)
        record.score = score
        record.classification = classification
        record.status = StatusEnum.processed.value
        record.error = None
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        record.status = StatusEnum.failed.value
        record.error = str(exc)
        db.add(record)
        db.commit()
