import time
import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Create an in-memory SQLite DB for tests (shared across connections).
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionLocal = sessionmaker(bind=engine)

# Patch the app's database module to use the test engine/sessionmaker before importing the app.
db_module = importlib.import_module("workflow_service.app.database")
db_module.engine = engine
db_module.SessionLocal = SessionLocal

# Import the model module(s) and create tables using the model metadata.
models_record = importlib.import_module("workflow_service.app.models.record")
models_record.Record.__table__.metadata.create_all(bind=engine)

# Now import the app and processing module so they pick up the overridden DB
from workflow_service.app.main import app  # noqa: E402
import workflow_service.app.services.processing as processing_module  # noqa: E402
from workflow_service.app.database import get_db  # noqa: E402

# Ensure the processing worker uses the test SessionLocal
processing_module.SessionLocal = SessionLocal

# Dependency override to use test sessions
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from fastapi.testclient import TestClient  # noqa: E402

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_post_record_and_processing_happens():
    payload = {
        "source": "test",
        "category": "integration",
        "payload": {"name": "IntegrationTest", "value": 1},
    }

    resp = client.post("/records", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    record_id = data["id"]

    # Trigger processing explicitly via the process endpoint
    p = client.post(f"/records/{record_id}/process")
    assert p.status_code == 200

    # poll until processed or timeout (short)
    last = None
    for _ in range(25):  # ~5 seconds max
        r = client.get(f"/records/{record_id}")
        assert r.status_code == 200
        last = r.json()
        if last.get("status") == "processed":
            break
        time.sleep(0.2)

    assert last is not None
    assert last["status"] == "processed"
    # Basic checks on processing side-effect (our dummy processor sets these values)
    assert "classification" in last
    assert "score" in last
