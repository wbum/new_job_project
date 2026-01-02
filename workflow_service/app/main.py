from fastapi import FastAPI
from workflow_service.app.api.records import router as records_router
from workflow_service.app.database import engine
from workflow_service.app import models

app = FastAPI(title="Workflow Automation & Reporting Service")

# Create database tables on startup (for development)
@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=engine)

app.include_router(records_router, prefix="", tags=["records"]) 

@app.get("/health")
async def health():
    return {"status": "ok"}
