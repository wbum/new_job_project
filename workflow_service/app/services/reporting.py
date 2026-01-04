from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..models.record import Record

ALLOWED_STATUSES = {"pending", "processed", "failed"}


def _apply_filters(query, status: Optional[str], category: Optional[str], date_from: Optional[datetime], date_to: Optional[datetime]):
    if status:
        query = query.filter(Record.status == status)
    if category:
        query = query.filter(Record.category == category)
    if date_from:
        query = query.filter(Record.created_at >= date_from)
    if date_to:
        query = query.filter(Record.created_at <= date_to)
    return query


def get_records(db: Session, *, status: Optional[str] = None, category: Optional[str] = None,
                created_after: Optional[datetime] = None, created_before: Optional[datetime] = None,
                limit: int = 50, offset: int = 0) -> Tuple[List[Record], int]:
    """Return a page of records and the total matching count (without pagination).

    newest-first ordering is applied.
    """
    base_q = db.query(Record)
    base_q = _apply_filters(base_q, status, category, created_after, created_before)

    total = base_q.count()

    items = base_q.order_by(Record.created_at.desc()).limit(limit).offset(offset).all()

    return items, total


def get_summary(db: Session, *, status: Optional[str] = None, category: Optional[str] = None,
                date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Dict[str, object]:
    """Return aggregated summary data for records.

    - totals by status
    - counts by category
    """
    # Validate status if provided
    if status and status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status: {status}")

    # Base filters applied to queries
    filters = []
    if status:
        filters.append(Record.status == status)
    if category:
        filters.append(Record.category == category)
    if date_from:
        filters.append(Record.created_at >= date_from)
    if date_to:
        filters.append(Record.created_at <= date_to)

    # Totals
    total_q = db.query(func.count(Record.id))
    if filters:
        total_q = total_q.filter(and_(*filters))
    total_all = total_q.scalar() or 0

    # Totals by status (regardless of category unless filtered)
    status_q = db.query(Record.status, func.count(Record.id)).group_by(Record.status)
    if filters:
        status_q = status_q.filter(and_(*filters))
    status_rows = status_q.all()
    totals = {"all": int(total_all), "pending": 0, "processed": 0, "failed": 0}
    for st, cnt in status_rows:
        if st in totals:
            totals[st] = int(cnt)

    # Counts by category
    cat_q = db.query(Record.category, func.count(Record.id)).group_by(Record.category)
    if status:
        # if status provided, include it in the category aggregation
        cat_q = cat_q.filter(Record.status == status)
    if date_from:
        cat_q = cat_q.filter(Record.created_at >= date_from)
    if date_to:
        cat_q = cat_q.filter(Record.created_at <= date_to)
    if category:
        cat_q = cat_q.filter(Record.category == category)

    by_category = [
        {"category": cat, "count": int(cnt)} for cat, cnt in cat_q.all()
    ]

    return {"totals": totals, "by_category": by_category}
