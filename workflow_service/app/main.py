from fastapi import FastAPI
from .api.records import router as records_router
from .api.reports import router as reports_router

app = FastAPI(title="Workflow Automation & Reporting Service")

app.include_router(records_router, prefix="", tags=["records"])
app.include_router(reports_router, prefix="", tags=["reports"])

@app.get("/health")
async def health():
    return {"status": "ok"}
