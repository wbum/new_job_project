from fastapi import APIRouter
from sqlalchemy import text

from ..database import engine

router = APIRouter()


@router.get("/health")
def health():
    """
    Health check endpoint with database connectivity check.
    Returns 200 if service and database are healthy, 500 if database is unreachable.
    """
    response = {
        "service": "ok",
        "version": "0.1.0",
        "database": {"status": "ok"}
    }
    
    # Check database connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
    except Exception as e:
        response["database"]["status"] = "error"
        response["database"]["error"] = str(e)
        # Return 500 status when database is down
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content=response)
    
    return response
