# workflow_service/tests/test_processing.py
import time
import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Create a shared in-memory engine so all connections (app, test, background worker)
# see the same database.
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine)

# Patch the app's database module to use the test engine/sessionmaker before importing the app.
db_module = importlib.import_module("workflow_service.app.database")
db_module.engine = engine
db_module.SessionLocal = SessionLocal

# Ensure the models' metadata is created in the test engine (so tables and columns exist).
models_record = importlib.import_module("workflow_service.app.models.record")
models_record.Record.__table__.metadata.create_all(bind=engine)

# Now import the FastAPI app and processing module so they pick up the test DB.
from workflow_service.app.main import app  # noqa: E402
import workflow_service.app.services.processing as processing_module  # noqa: E402
from workflow_service.app.database import get_db  # noqa: E402

# Ensure the background worker uses the test SessionLocal
processing_module.SessionLocal = SessionLocal

# Override get_db dependency to yield test sessions
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

from fastapi.testclient import TestClient  # noqa: E402
client = TestClient(app)


def test_create_and_process_record():
    payload = {"source": "test", "category": "unit", "payload": {"k": "v"}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    record_id = data["id"]

    # poll until processed
    last = None
    for _ in range(25):
        rr = client.get(f"/records/{record_id}")
        assert rr.status_code == 200
        last = rr.json()
        if last.get("status") == "processed":
            break
        time.sleep(0.2)

    assert last is not None
    assert last["status"] == "processed"
