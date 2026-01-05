from fastapi import FastAPI
from .api import records
from .api import health  # existing
from .api import reports  # new

from .database import engine, Base

app = FastAPI(title="Workflow Service")

# Development convenience: create tables if missing
Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(records.router)
app.include_router(reports.router)
