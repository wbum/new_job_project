import importlib
import time

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

# Ensure reporting service uses the test session if needed
processing_module = importlib.import_module("workflow_service.app.services.processing")
processing_module.SessionLocal = SessionLocal


# Override dependency
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _create_record_and_process(payload, do_process=False):
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    data = r.json()
    rid = data["id"]
    if do_process:
        p = client.post(f"/records/{rid}/process")
        assert p.status_code == 200
    return rid


def test_summary_counts():
    # Create records: 2 processed, 1 failed, 1 pending
    p_good1 = {"source": "t", "category": "alpha", "payload": {"priority": 3}}
    p_good2 = {"source": "t", "category": "alpha", "payload": {"priority": 4}}
    p_bad = {"source": "t", "category": "beta", "payload": {"priority": "xxx"}}
    p_pending = {"source": "t", "category": "beta", "payload": {"k": "v"}}

    _create_record_and_process(p_good1, do_process=True)
    _create_record_and_process(p_good2, do_process=True)
    _create_record_and_process(p_bad, do_process=True)
    _create_record_and_process(p_pending, do_process=False)

    # Wait briefly for any processing to commit (processing is synchronous, but keep small sleep)
    time.sleep(0.1)

    # Get summary unfiltered
    resp = client.get("/reports/summary")
    assert resp.status_code == 200
    data = resp.json()
    totals = data["totals"]
    assert totals["all"] == 4
    assert totals["processed"] == 2
    assert totals["failed"] == 1
    assert totals["pending"] == 1

    # Summary filtered by category=alpha
    resp2 = client.get("/reports/summary?category=alpha")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["totals"]["all"] == 2
    assert data2["totals"]["processed"] == 2


def test_list_and_filtering():
    # Create several records of different statuses and categories
    a1 = {"source": "t", "category": "catA", "payload": {"priority": 1}}
    a2 = {"source": "t", "category": "catA", "payload": {"priority": 2}}
    b1 = {"source": "t", "category": "catB", "payload": {"priority": "not-n"}}  # will fail

    _create_record_and_process(a1, do_process=True)
    _create_record_and_process(a2, do_process=True)
    _create_record_and_process(b1, do_process=True)

    # List records with status=processed
    r = client.get("/records?status=processed")
    assert r.status_code == 200
    payload = r.json()
    assert payload["count"] >= 2
    for item in payload["items"]:
        assert item["status"] == "processed"

    # Limit enforcement: request large limit and ensure it caps to 200
    r2 = client.get("/records?limit=500")
    assert r2.status_code == 200
    p2 = r2.json()
    assert p2["count"] <= 200


def test_sorting():
    """Test sorting functionality on list endpoint."""
    # Create records with different sources and categories
    records = [
        {"source": "api", "category": "alpha", "payload": {"x": 1}},
        {"source": "web", "category": "beta", "payload": {"x": 2}},
        {"source": "api", "category": "gamma", "payload": {"x": 3}},
        {"source": "mobile", "category": "alpha", "payload": {"x": 4}},
    ]

    record_ids = []
    for rec in records:
        rid = _create_record_and_process(rec, do_process=False)
        record_ids.append(rid)
        time.sleep(0.01)  # Small delay to ensure different created_at times

    # Test sorting by created_at desc (default)
    r = client.get("/records?sort_by=created_at&sort_order=desc")
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    assert len(items) >= 4
    # Most recent should be first
    created_ats = [item["created_at"] for item in items[:4]]
    assert created_ats == sorted(created_ats, reverse=True)

    # Test sorting by created_at asc
    r = client.get("/records?sort_by=created_at&sort_order=asc")
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    created_ats = [item["created_at"] for item in items[:4]]
    assert created_ats == sorted(created_ats)

    # Test sorting by source asc
    r = client.get("/records?sort_by=source&sort_order=asc")
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    sources = [item["source"] for item in items[:4]]
    assert sources == sorted(sources)

    # Test sorting by category desc
    r = client.get("/records?sort_by=category&sort_order=desc")
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    categories = [item["category"] for item in items[:4]]
    assert categories == sorted(categories, reverse=True)

    # Test sorting by status (all should be pending)
    r = client.get("/records?sort_by=status&sort_order=asc")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 4


def test_sorting_validation():
    """Test that sorting validation works correctly."""
    # Valid parameters should succeed
    r = client.get("/records?sort_by=status&sort_order=asc")
    assert r.status_code == 200

    r = client.get("/records?sort_by=category&sort_order=desc")
    assert r.status_code == 200

    r = client.get("/records?sort_by=created_at")
    assert r.status_code == 200

    # Note: Invalid sort parameters would be rejected by FastAPI's validation
    # but testing this requires fixing the error handler first (ErrorBody schema issue)
