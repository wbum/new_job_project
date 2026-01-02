from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.models.record import Record

client = TestClient(app)

def setup_module(module):
    # create tables
    Base.metadata.create_all(bind=engine)

def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

def test_create_record():
    payload = {"source": "test-source", "category": "test-category", "payload": {"key": "value"}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["source"] == "test-source"
    assert data["category"] == "test-category"
    assert data["payload"] == {"key": "value"}
