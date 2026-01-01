from fastapi import FastAPI
from app.api.records import router as records_router

app = FastAPI(
    title="Workflow Automation & Reporting Service",
    description=(
        "Automates structured workflows, applies deterministic business rules, "
        "and generates auditable summary reports. Built with FastAPI, SQLAlchemy, "
        "and PostgreSQL (SQLite for local development)."
    ),
    version="0.1.0",
    contact={"name": "wbum"},
    license_info={"name": "MIT"},
)

app.include_router(records_router, prefix="", tags=["records"]) 

@app.get("/health", tags=["health"])
async def health():
    """
    Health check endpoint. Returns {"status": "ok"} when the service is running.
    """
    return {"status": "ok"}
