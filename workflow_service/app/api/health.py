from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Health check endpoint that validates:
    - API is responding
    - Database connection is working
    """
    health_status = {
        "status": "ok",
        "service": "workflow_service",
        "checks": {"api": "ok", "database": "unknown"},
    }

    # Check database connectivity
    try:
        # Simple query to verify DB connection
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = f"error: {str(e)}"
        # Return 503 Service Unavailable if database is down
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
        ) from e

    return health_status
