"""
Tests for error handling and failure modes in the workflow service.
"""
from fastapi.testclient import TestClient
from workflow_service.app.main import app
from workflow_service.app.database import Base, engine, SessionLocal
from workflow_service.app.models.record import Record, StatusEnum

client = TestClient(app)


def setup_module(module):
    """Create tables before tests."""
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    """Drop tables after tests."""
    Base.metadata.drop_all(bind=engine)


def test_error_response_structure():
    """Test that error responses have the correct structure."""
    # Try to get a non-existent record
    response = client.get("/records/nonexistent-id")
    
    assert response.status_code == 404
    data = response.json()
    
    # Check error structure
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert data["error"]["code"] == "RECORD_NOT_FOUND"
    
    # Check request ID is present
    assert "request_id" in data
    
    # Check X-Request-ID header
    assert "X-Request-ID" in response.headers


def test_missing_record_returns_404():
    """Test that requesting a missing record returns 404 with RECORD_NOT_FOUND code."""
    response = client.get("/records/missing-record-id")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "RECORD_NOT_FOUND"
    assert data["error"]["message"] == "record not found"
    assert "request_id" in data


def test_process_missing_record_returns_404():
    """Test that processing a missing record returns 404."""
    response = client.post("/records/missing-record-id/process")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "RECORD_NOT_FOUND"


def test_process_already_processed_record_returns_409():
    """Test that processing an already processed record returns 409 conflict."""
    # Create a record
    create_response = client.post("/records", json={
        "source": "api",
        "category": "test",
        "payload": {"test": "data"}
    })
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]
    
    # Process it
    process_response = client.post(f"/records/{record_id}/process")
    assert process_response.status_code == 200
    
    # Try to process again - should get conflict
    conflict_response = client.post(f"/records/{record_id}/process")
    
    assert conflict_response.status_code == 409
    data = conflict_response.json()
    assert data["error"]["code"] == "ALREADY_PROCESSED"
    assert data["error"]["message"] == "record is not pending"
    assert "request_id" in data


def test_invalid_payload_returns_422():
    """Test that invalid request payload returns 422 with validation details."""
    # Missing required fields
    response = client.post("/records", json={"invalid": "data"})
    
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "request validation failed"
    assert "details" in data["error"]
    assert "errors" in data["error"]["details"]
    assert "request_id" in data


def test_summary_with_empty_database():
    """Test that summary endpoint returns zeros when database is empty."""
    # Clear database
    db = SessionLocal()
    try:
        db.query(Record).delete()
        db.commit()
    finally:
        db.close()
    
    response = client.get("/reports/summary")
    
    assert response.status_code == 200
    data = response.json()
    assert "totals" in data
    assert data["totals"]["all"] == 0
    assert data["totals"]["pending"] == 0
    assert data["totals"]["processed"] == 0
    assert data["totals"]["failed"] == 0


def test_request_id_propagation():
    """Test that custom X-Request-ID is propagated through the system."""
    custom_request_id = "test-request-123"
    
    response = client.get(
        "/records/missing-id",
        headers={"X-Request-ID": custom_request_id}
    )
    
    # Check that our custom request ID is returned
    assert response.headers.get("X-Request-ID") == custom_request_id
    
    # Also check it's in the error response body
    data = response.json()
    assert data["request_id"] == custom_request_id


def test_health_endpoint_structure():
    """Test that health endpoint returns expected structure."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "database" in data
    assert data["service"] == "ok"
    assert data["version"] == "0.1.0"
    assert "status" in data["database"]
