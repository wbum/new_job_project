from fastapi.testclient import TestClient
import time
import importlib

# Import app and DB get_db just like the repo's tests do.
from app.main import app  # keep legacy import used by existing tests
from app.database import Base, get_db, engine, SessionLocal  # ensure these exist

# Create tables in the test (file-backed) DB if necessary. If engine is SQLite in-memory this is harmless.
Base.metadata.create_all(bind=engine)

# Override get_db for tests to ensure clean sessions per test
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_and_process_record():
    payload = {"source": "test", "category": "unit", "payload": {"k": "v"}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    record_id = data["id"]

    # Trigger processing
    p = client.post(f"/records/{record_id}/process")
    assert p.status_code == 200

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


def test_create_and_process_record_with_bad_payload_rejected():
    # Create record with a payload that will cause processing to fail
    payload = {"source": "test", "category": "unit", "payload": {"priority": "not-a-number"}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    record_id = data["id"]

    # Trigger processing (should mark failed)
    p = client.post(f"/records/{record_id}/process")
    assert p.status_code == 200

    rr = client.get(f"/records/{record_id}")
    assert rr.status_code == 200
    last = rr.json()
    assert last["status"] == "failed"
    assert last["result"] is not None or last["error"]
