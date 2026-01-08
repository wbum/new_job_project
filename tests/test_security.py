"""Tests for security features (API key authentication)."""

import importlib
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup an in-memory SQLite DB shared by connections (StaticPool)
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionLocal = sessionmaker(bind=engine)

# Patch app.database to use test engine/session BEFORE importing app
db_module = importlib.import_module("workflow_service.app.database")
db_module.engine = engine
db_module.SessionLocal = SessionLocal

# Create tables from model metadata
models_record = importlib.import_module("workflow_service.app.models.record")
models_record.Record.__table__.metadata.create_all(bind=engine)

# Import app and services
from workflow_service.app.database import get_db  # noqa: E402
from workflow_service.app.main import app  # noqa: E402


# Override dependency
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_read_endpoints_public_access():
    """Test that read endpoints (GET) don't require authentication."""
    # Health check
    r = client.get("/health")
    assert r.status_code == 200

    # Version endpoint
    r = client.get("/version")
    assert r.status_code == 200

    # List records
    r = client.get("/records")
    assert r.status_code == 200

    # Get summary
    r = client.get("/reports/summary")
    assert r.status_code == 200


def test_write_without_api_key_dev_mode():
    """Test that write endpoints work without API key in dev mode (no API_KEY env var)."""
    # Ensure API_KEY is not set (dev mode)
    os.environ.pop("API_KEY", None)

    # Reload config to pick up env changes
    config_module = importlib.import_module("workflow_service.app.config")
    importlib.reload(config_module)

    # Create record without API key
    payload = {"source": "test", "category": "test", "payload": {"x": 1}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    record_id = r.json()["id"]

    # Process record without API key
    r = client.post(f"/records/{record_id}/process")
    assert r.status_code in [200, 409]  # 409 if already processed


def test_write_with_missing_api_key():
    """Test that write endpoints return 401 when API key is required but missing."""
    # Set API_KEY env var
    os.environ["API_KEY"] = "test-secret-key-123"

    # Reload config and security module to pick up env changes
    config_module = importlib.import_module("workflow_service.app.config")
    security_module = importlib.import_module("workflow_service.app.core.security")
    importlib.reload(config_module)
    importlib.reload(security_module)

    # Try to create record without API key
    payload = {"source": "test", "category": "test", "payload": {"x": 1}}
    r = client.post("/records", json=payload)
    assert r.status_code == 401
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "request_id" in body

    # Cleanup
    os.environ.pop("API_KEY", None)
    importlib.reload(config_module)
    importlib.reload(security_module)


def test_write_with_invalid_api_key():
    """Test that write endpoints return 401 when API key is invalid."""
    # Set API_KEY env var
    os.environ["API_KEY"] = "test-secret-key-123"

    # Reload config and security module
    config_module = importlib.import_module("workflow_service.app.config")
    security_module = importlib.import_module("workflow_service.app.core.security")
    importlib.reload(config_module)
    importlib.reload(security_module)

    # Try to create record with wrong API key
    payload = {"source": "test", "category": "test", "payload": {"x": 1}}
    headers = {"X-API-Key": "wrong-key"}
    r = client.post("/records", json=payload, headers=headers)
    assert r.status_code == 401
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"

    # Cleanup
    os.environ.pop("API_KEY", None)
    importlib.reload(config_module)
    importlib.reload(security_module)


def test_write_with_valid_api_key():
    """Test that write endpoints work with valid API key."""
    # Set API_KEY env var
    os.environ["API_KEY"] = "test-secret-key-123"

    # Reload config and security module
    config_module = importlib.import_module("workflow_service.app.config")
    security_module = importlib.import_module("workflow_service.app.core.security")
    importlib.reload(config_module)
    importlib.reload(security_module)

    # Create record with correct API key
    payload = {"source": "test", "category": "test", "payload": {"x": 1}}
    headers = {"X-API-Key": "test-secret-key-123"}
    r = client.post("/records", json=payload, headers=headers)
    assert r.status_code == 201
    record_id = r.json()["id"]

    # Process record with correct API key
    r = client.post(f"/records/{record_id}/process", headers=headers)
    assert r.status_code in [200, 409]

    # Cleanup
    os.environ.pop("API_KEY", None)
    importlib.reload(config_module)
    importlib.reload(security_module)
