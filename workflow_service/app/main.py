from fastapi import FastAPI
from app.database import engine, Base
from app.api.records import router as records_router

# Create tables on startup for development convenience
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workflow Automation & Reporting Service")

app.include_router(records_router, prefix="", tags=["records"]) 

@app.get("/health")
async def health():
    return {"status": "ok"}
