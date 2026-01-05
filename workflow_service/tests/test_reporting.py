import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.record import Record, StatusEnum

client = TestClient(app)


def setup_module(module):
    """Create tables before tests."""
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    """Clean up after all tests in this module."""
    Base.metadata.drop_all(bind=engine)


def test_summary_counts():
    """Test that summary endpoint returns correct counts by status and category."""
    # Clear any previous data
    db = SessionLocal()
    db.query(Record).delete()
    db.commit()
    
    # Create test records directly in the database with controlled statuses
    rec1 = Record(source="api", category="attendance", payload={"test": 1}, status=StatusEnum.pending.value)
    rec2 = Record(source="api", category="attendance", payload={"test": 2}, status=StatusEnum.pending.value)
    rec3 = Record(source="web", category="payroll", payload={"test": 3}, status=StatusEnum.processed.value)
    rec4 = Record(source="web", category="hr", payload={"test": 4}, status=StatusEnum.processed.value)
    
    db.add_all([rec1, rec2, rec3, rec4])
    db.commit()
    db.close()
    
    # Get summary without filters
    r = client.get("/reports/summary")
    assert r.status_code == 200
    data = r.json()
    
    assert "generated_at" in data
    assert "filters" in data
    assert "totals" in data
    assert "by_category" in data
    
    # Check totals
    totals = data["totals"]
    assert totals["all"] == 4
    assert totals["pending"] == 2
    assert totals["processed"] == 2
    assert totals["failed"] == 0
    
    # Check by_category
    by_category = data["by_category"]
    categories = {item["category"]: item["count"] for item in by_category}
    assert categories.get("attendance", 0) == 2
    assert categories.get("payroll", 0) == 1
    assert categories.get("hr", 0) == 1
    
    # Test filtered summary by status
    r = client.get("/reports/summary?status=processed")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["all"] == 2
    assert data["totals"]["processed"] == 2
    
    # Test filtered summary by category
    r = client.get("/reports/summary?category=attendance")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["all"] == 2
    
    # Test invalid status
    r = client.get("/reports/summary?status=invalid")
    assert r.status_code == 400


def test_filtering_and_list_endpoint():
    """Test that the list endpoint returns filtered and paginated records."""
    # Clear previous data by creating a new session
    db = SessionLocal()
    db.query(Record).delete()
    db.commit()
    
    # Create test records directly in the database with controlled statuses
    rec1 = Record(source="api", category="attendance", payload={"index": 1}, status=StatusEnum.processed.value)
    rec2 = Record(source="api", category="payroll", payload={"index": 2}, status=StatusEnum.processed.value)
    rec3 = Record(source="web", category="attendance", payload={"index": 3}, status=StatusEnum.processed.value)
    rec4 = Record(source="web", category="hr", payload={"index": 4}, status=StatusEnum.pending.value)
    rec5 = Record(source="api", category="attendance", payload={"index": 5}, status=StatusEnum.pending.value)
    
    db.add_all([rec1, rec2, rec3, rec4, rec5])
    db.commit()
    db.close()
    
    # Test list all records
    r = client.get("/records")
    assert r.status_code == 200
    data = r.json()
    
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["limit"] == 50
    assert data["offset"] == 0
    
    # Test filter by status
    r = client.get("/records?status=processed")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Test filter by category
    r = client.get("/records?category=attendance")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Test pagination
    r = client.get("/records?limit=2&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
    
    r = client.get("/records?limit=2&offset=2")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["offset"] == 2
    
    # Test combined filters
    r = client.get("/records?status=processed&category=attendance")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    
    # Test invalid status
    r = client.get("/records?status=invalid")
    assert r.status_code == 400
    
    # Test limit bounds
    r = client.get("/records?limit=201")
    assert r.status_code == 422  # Validation error
    
    # Verify items structure
    r = client.get("/records?limit=1")
    assert r.status_code == 200
    data = r.json()
    item = data["items"][0]
    
    assert "id" in item
    assert "created_at" in item
    assert "status" in item
    assert "source" in item
    assert "category" in item
    assert "payload" in item
    assert "classification" in item
    assert "score" in item
    assert "error" in item
