from fastapi.testclient import TestClient
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workflow_service.app.main import app
from workflow_service.app.database import Base, get_db
import workflow_service.app.services.processing as processing_module

# Use an in-memory SQLite DB for tests
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# Create tables in the test database
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Ensure the background worker uses the same SessionLocal as the test DB.
# processing_module.SessionLocal was set at import time to the app engine; override it.
processing_module.SessionLocal = SessionLocal

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
