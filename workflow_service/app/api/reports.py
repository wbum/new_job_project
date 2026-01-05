from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_db
from ..services import reporting

router = APIRouter()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # handle trailing 'Z' as UTC
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid datetime: {value}")


@router.get("/reports/summary")
def get_summary_endpoint(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """
    Summary report with optional filters.
    Query params:
      - status: pending|processed|failed
      - category: string
      - date_from, date_to: ISO date or datetime (e.g. 2026-01-04 or 2026-01-04T12:34:56Z)
    """
    # parse datetimes
    dt_from = _parse_iso_datetime(date_from)
    dt_to = _parse_iso_datetime(date_to)

    # validate date range
    if dt_from and dt_to and dt_from > dt_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from > date_to")

    # validate status (reporting will raise ValueError as well)
    try:
        summary = reporting.get_summary(db, status=status, category=category, date_from=dt_from, date_to=dt_to)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "filters": {"status": status, "category": category, "date_from": date_from, "date_to": date_to},
        "totals": summary["totals"],
        "by_category": summary["by_category"],
    }
