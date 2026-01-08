import os

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Health check endpoint with database connectivity verification.

    Returns:
        200 OK: Service is healthy and database is accessible
        503 Service Unavailable: Database connection failed
    """
    try:
        # Simple DB connectivity check
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)},
        )


@router.get("/version")
def version():
    """
    Version information endpoint.

    Returns application version and git commit SHA (if available).
    """
    return {
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "commit": os.getenv("GIT_COMMIT", "unknown"),
        "environment": os.getenv("APP_ENV", "dev"),
    }
