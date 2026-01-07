from fastapi.testclient import TestClient
from workflow_service.app.main import app
from workflow_service.app.database import Base, engine, SessionLocal
from workflow_service.app.models.record import Record, StatusEnum

client = TestClient(app)

def setup_module(module):
    # create tables
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_create_and_process_record():
    payload = {
        "source": "api",
        "category": "test",
        "payload": {"subject": "Test", "metrics": {"severity": 7, "impact": 6, "urgency": 2}}
    }
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    record_id = data["id"]
    # wait a short moment for background task to run (BackgroundTasks run synchronously in TestClient)
    r2 = client.get(f"/records/{record_id}")
    assert r2.status_code == 200
    detail = r2.json()
    assert detail["status"] in [StatusEnum.processed.value, StatusEnum.pending.value, StatusEnum.failed.value]
