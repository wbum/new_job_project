from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models.record import Record


def get_records(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Record], int]:
    """
    Query records with optional filters and pagination.
    Returns (items, total_count).
    """
    query = db.query(Record)

    if status:
        query = query.filter(Record.status == status)
    if category:
        query = query.filter(Record.category == category)
    if created_after:
        query = query.filter(Record.created_at >= created_after)
    if created_before:
        query = query.filter(Record.created_at <= created_before)

    total = query.count()
    items = query.order_by(Record.created_at.desc()).limit(limit).offset(offset).all()

    return items, total
