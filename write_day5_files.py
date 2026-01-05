from pathlib import Path

files = {
    "workflow_service/app/api/reports.py": r'''from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_db
from ..services import reporting

router = APIRouter()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # handle trailing 'Z' as UTC
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid datetime: {value}")


@router.get("/reports/summary")
def get_summary_endpoint(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
):
    """
    Summary report with optional filters.
    Query params:
      - status: pending|processed|failed
      - category: string
      - date_from, date_to: ISO date or datetime (e.g. 2026-01-04 or 2026-01-04T12:34:56Z)
    """
    # parse datetimes
    dt_from = _parse_iso_datetime(date_from)
    dt_to = _parse_iso_datetime(date_to)

    # validate date range
    if dt_from and dt_to and dt_from > dt_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from > date_to")

    # validate status (reporting will raise ValueError as well)
    try:
        summary = reporting.get_summary(db, status=status, category=category, date_from=dt_from, date_to=dt_to)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "filters": {"status": status, "category": category, "date_from": date_from, "date_to": date_to},
        "totals": summary["totals"],
        "by_category": summary["by_category"],
    }
''',

    "workflow_service/app/api/records.py": r'''from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.record import Record
from ..schemas.record import RecordCreate, RecordRead
from ..services import processing, reporting

router = APIRouter()


def _fetch_record(db: Session, record_id: str) -> Record:
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="record not found")
    return rec


def _to_read_model(rec: Record) -> RecordRead:
    payload = {}
    try:
        payload = json.loads(rec.payload)
    except Exception:
        payload = {}

    result = None
    if rec.result:
        try:
            result = json.loads(rec.result)
        except Exception:
            result = None

    return RecordRead(
        id=rec.id,
        created_at=rec.created_at,
        status=rec.status,
        source=rec.source,
        category=rec.category,
        payload=payload,
        result=result,
        classification=rec.classification,
        score=rec.score,
        error=rec.error,
    )


@router.post("/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rec = Record(
        source=payload.source,
        category=payload.category,
        payload=json.dumps(payload.payload),
        status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Do not auto-process here (explicit trigger endpoint exists)
    return _to_read_model(rec)


def _parse_iso_datetime_optional(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid datetime: {value}")


@router.get("/records", response_model=dict)
def list_records(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List records with filters and pagination.
    - status, category (optional)
    - created_after, created_before (ISO date/time)
    - limit (default 50, max 200), offset (default 0)
    Returns: { items: [...], count: <page_count>, total: <total_matching> }
    """
    # enforce max limit
    if limit > 200:
        limit = 200

    # parse datetimes
    dt_after = _parse_iso_datetime_optional(created_after)
    dt_before = _parse_iso_datetime_optional(created_before)

    # fetch via service layer
    items, total = reporting.get_records(
        db,
        status=status,
        category=category,
        created_after=dt_after,
        created_before=dt_before,
        limit=limit,
        offset=offset,
    )

    return {"items": [_to_read_model(i) for i in items], "count": len(items), "total": total}


@router.get("/records/{record_id}", response_model=RecordRead)
def get_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)
    return _to_read_model(rec)


@router.post("/records/{record_id}/process", response_model=RecordRead)
def post_process_record(record_id: str, db: Session = Depends(get_db)):
    rec = _fetch_record(db, record_id)

    if rec.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="record is not pending")

    # Run processing synchronously (service takes care of sessions & persistence)
    processing.process_record(rec.id)

    # Refresh record from DB to return updated state
    rec = db.query(Record).filter(Record.id == record_id).first()
    return _to_read_model(rec)
''',

    "workflow_service/app/main.py": r'''from fastapi import FastAPI
from .api import records
from .api import health  # existing
from .api import reports  # new

from .database import engine, Base

app = FastAPI(title="Workflow Service")

# Development convenience: create tables if missing
Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(records.router)
app.include_router(reports.router)
''',

    "tests/test_reporting.py": r'''import importlib
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

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
from workflow_service.app.main import app  # noqa: E402
from workflow_service.app.database import get_db  # noqa: E402

# Ensure reporting service uses the test session if needed
reporting_module = importlib.import_module("workflow_service.app.services.reporting")
processing_module = importlib.import_module("workflow_service.app.services.processing")
processing_module.SessionLocal = SessionLocal
reporting_module  # (no-op)

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

    id1 = _create_record_and_process(p_good1, do_process=True)
    id2 = _create_record_and_process(p_good2, do_process=True)
    id3 = _create_record_and_process(p_bad, do_process=True)
    id4 = _create_record_and_process(p_pending, do_process=False)

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

    id_a1 = _create_record_and_process(a1, do_process=True)
    id_a2 = _create_record_and_process(a2, do_process=True)
    id_b1 = _create_record_and_process(b1, do_process=True)

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
''',
}

for path, content in files.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    print("Wrote", p)