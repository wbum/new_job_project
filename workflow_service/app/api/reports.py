from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.reporting import get_summary, ALLOWED_STATUSES


router = APIRouter()


@router.get("/reports/summary")
def get_summary_report(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    db: Session = Depends(get_db)
):
    """
    Get summary report with optional filters.
    
    Returns aggregated counts by status and category.
    """
    # Validate status if provided
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Allowed values: {', '.join(ALLOWED_STATUSES)}"
        )
    
    # Parse dates
    parsed_date_from = None
    parsed_date_to = None
    
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format.")
    
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format.")
    
    # Validate date range
    if parsed_date_from and parsed_date_to and parsed_date_from > parsed_date_to:
        raise HTTPException(status_code=400, detail="date_from must be less than or equal to date_to")
    
    # Call service layer
    try:
        summary_data = get_summary(
            db,
            status=status,
            category=category,
            date_from=parsed_date_from,
            date_to=parsed_date_to
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Build response
    response = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "filters": {
            "status": status,
            "category": category,
            "date_from": date_from,
            "date_to": date_to
        },
        "totals": summary_data["totals"],
        "by_category": summary_data["by_category"]
    }
    
    return response
