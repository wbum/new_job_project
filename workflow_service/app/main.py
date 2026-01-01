from fastapi import FastAPI
from app.api.records import router as records_router

app = FastAPI(title="Workflow Automation & Reporting Service")

app.include_router(records_router, prefix="", tags=["records"]) 

@app.get("/health")
async def health():
    return {"status": "ok"}
