#!/usr/bin/env bash
set -euo pipefail

BRANCH="day6-prod-shape"

echo "==> Creating branch $BRANCH (will fail if already exists)"
git checkout -b "$BRANCH"

echo "==> Creating directories"
mkdir -p workflow_service/app
mkdir -p workflow_service/app/api
mkdir -p workflow_service/app/services
mkdir -p workflow_service/tests

backup_if_exists() {
  if [ -f "$1" ]; then
    echo "Backing up existing $1 -> ${1}.bak"
    mv "$1" "${1}.bak"
  fi
}

echo "==> Writing workflow_service/app/exceptions.py"
backup_if_exists workflow_service/app/exceptions.py
cat > workflow_service/app/exceptions.py <<'PY'
from __future__ import annotations

from typing import Any, Dict, Optional


class DomainError(Exception):
    """Base class for domain-level errors that should be returned to clients."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "internal server error"
    details: Optional[Any] = None

    def __init__(self, message: Optional[str] = None, details: Optional[Any] = None):
        if message:
            self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundError(DomainError):
    status_code = 404
    code = "RECORD_NOT_FOUND"
    message = "record not found"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"
    message = "conflict"


def format_error_response(exc: DomainError, request_id: str | None = None) -> Dict[str, object]:
    body: Dict[str, object] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }
    if exc.details is not None:
        body["error"]["details"] = exc.details
    if request_id:
        body["request_id"] = request_id
    return body
PY

echo "==> Writing workflow_service/app/main.py"
backup_if_exists workflow_service/app/main.py
cat > workflow_service/app/main.py <<'PY'
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import engine
from .exceptions import DomainError, format_error_response

# import routers (use relative imports)
from .api import records, health

# setup logger
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = logging.getLogger("workflow")
handler = logging.StreamHandler()
# keep formatter simple; we emit JSON in messages
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(LOG_LEVEL)

app = FastAPI(title="Workflow Service", version="0.1.0")

# include routers
app.include_router(records.router)
app.include_router(health.router)

try:
    # reports router may exist
    from .api import reports

    app.include_router(reports.router)
except Exception:
    pass


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Callable):
    # request id propagation
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start_ts = time.time()
    try:
        response = await call_next(request)
    except Exception:
        # let exception handlers handle logging
        raise

    duration_ms = int((time.time() - start_ts) * 1000)
    response.headers["X-Request-ID"] = request_id

    log_line = {
        "ts": int(start_ts),
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
    }
    # log as JSON string so it's easy to parse
    logger.info(json.dumps(log_line))
    return response


# Domain error handler
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    request_id = getattr(request.state, "request_id", None)
    body = format_error_response(exc, request_id)
    logger.info(json.dumps({"event": "domain_error", "request_id": request_id, "code": exc.code, "message": exc.message}))
    return JSONResponse(status_code=exc.status_code, content=body, headers={"X-Request-ID": request_id or ""})


# Validation error -> 422 with standardized shape
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    details = exc.errors() if hasattr(exc, "errors") else str(exc)
    body = {
        "error": {"code": "VALIDATION_ERROR", "message": "request validation failed", "details": details},
        "request_id": request_id,
    }
    logger.info(json.dumps({"event": "validation_error", "request_id": request_id, "details": details}))
    return JSONResponse(status_code=422, content=body, headers={"X-Request-ID": request_id or ""})


# Catch-all handler
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    # log full traceback to server logs
    logger.exception(json.dumps({"event": "unhandled_exception", "request_id": request_id, "exc": str(exc)}))
    body = {"error": {"code": "INTERNAL_ERROR", "message": "internal server error"}, "request_id": request_id}
    return JSONResponse(status_code=500, content=body, headers={"X-Request-ID": request_id or ""})
PY

echo "==> Writing workflow_service/app/api/health.py"
backup_if_exists workflow_service/app/api/health.py
cat > workflow_service/app/api/health.py <<'PY'
from fastapi import APIRouter
from sqlalchemy import text

from ..database import engine

router = APIRouter(prefix="/health")


@router.get("/live")
def live():
    return {"service": "ok", "version": "0.1.0"}


@router.get("")
def health():
    # Basic DB connectivity check
    db_status = {"status": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = {"status": "error", "error": str(exc)}
        return {"service": "error", "version": "0.1.0", "database": db_status}
    return {"service": "ok", "version": "0.1.0", "database": db_status}
PY

echo "==> Writing workflow_service/app/api/records.py"
backup_if_exists workflow_service/app/api/records.py
cat > workflow_service/app/api/records.py <<'PY'
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.record import Record
from ..schemas.record import RecordCreate, RecordRead
from ..services import processing, reporting
from ..exceptions import NotFoundError, ConflictError

router = APIRouter()


def _fetch_record(db: Session, record_id: str) -> Record:
    rec = db.query(Record).filter(Record.id == record_id).first()
    if not rec:
        raise NotFoundError()
    return rec


def _to_read_model(rec: Record) -> RecordRead:
    payload = {}
    try:
        payload = json.loads(getattr(rec, "payload", "{}"))
    except Exception:
        payload = {}

    result = None
    raw_result = getattr(rec, "result", None)
    if raw_result:
        try:
            result = json.loads(raw_result)
        except Exception:
            result = None

    classification = getattr(rec, "classification", None)
    score = getattr(rec, "score", None)
    error = getattr(rec, "error", None)
    created_at = getattr(rec, "created_at", None)

    return RecordRead(
        id=rec.id,
        created_at=created_at,
        status=rec.status,
        source=rec.source,
        category=rec.category,
        payload=payload,
        result=result,
        classification=classification,
        score=score,
        error=error,
    )


@router.post("/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    rec = Record(source=payload.source, category=payload.category, payload=json.dumps(payload.payload), status="pending")
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _to_read_model(rec)


@router.get("/records", response_model=dict)
def list_records(
    status: Optional[str] = None,
    category: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    # enforce max limit
    if limit > 200:
        limit = 200

    # parse datetimes
    def _parse_iso_datetime_optional(value: Optional[str]):
        if not value:
            return None
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            from datetime import datetime as _dt

            return _dt.fromisoformat(value)
        except Exception:
            return None

    dt_after = _parse_iso_datetime_optional(created_after)
    dt_before = _parse_iso_datetime_optional(created_before)

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
        raise ConflictError(message="record is not pending", details={"record_id": record_id})

    # Run processing synchronously (service takes care of sessions & persistence)
    processing.process_record(rec.id)

    rec = db.query(Record).filter(Record.id == record_id).first()
    return _to_read_model(rec)
PY

echo "==> Writing workflow_service/app/services/processing.py"
backup_if_exists workflow_service/app/services/processing.py
cat > workflow_service/app/services/processing.py <<'PY'
from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.record import Record

logger = logging.getLogger("workflow")


def process_record(record_id: str) -> None:
    db: Session = SessionLocal()
    try:
        rec: Optional[Record] = db.query(Record).filter(Record.id == record_id).first()
        if not rec:
            logger.info(json.dumps({"event": "process_missing", "record_id": record_id}))
            return

        old_status = rec.status
        try:
            # Place actual processing logic here. For now, keep prior behavior:
            # Simulate processing result if no existing result exists.
            # Replace with your real processing logic.
            result_obj = {"processed": True}
            rec.result = json.dumps(result_obj)
            rec.status = "processed"
            db.add(rec)
            db.commit()
            logger.info(
                json.dumps(
                    {
                        "event": "status_transition",
                        "record_id": record_id,
                        "old_status": old_status,
                        "new_status": rec.status,
                    }
                )
            )
        except Exception as e:
            db.rollback()
            rec.status = "failed"
            rec.error = str(e)
            db.add(rec)
            db.commit()
            logger.exception(json.dumps({"event": "processing_failed", "record_id": record_id, "error": str(e)}))
    finally:
        db.close()
PY

echo "==> Writing workflow_service/tests/test_errors.py"
backup_if_exists workflow_service/tests/test_errors.py
cat > workflow_service/tests/test_errors.py <<'PY'
from fastapi.testclient import TestClient
from workflow_service.app.main import app
from workflow_service.app.database import Base, engine
from workflow_service.app.models.record import Record

client = TestClient(app)


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


def test_process_missing_record_returns_404():
    r = client.post("/records/nonexistent-id/process")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "RECORD_NOT_FOUND"
    assert "request_id" in body or "X-Request-ID" in r.headers


def test_reprocessing_conflict_returns_409():
    payload = {"source": "t", "category": "test", "payload": {"foo": "bar"}}
    r = client.post("/records", json=payload)
    assert r.status_code == 201
    rec = r.json()
    record_id = rec["id"]

    # manually mark processed
    from workflow_service.app.database import SessionLocal

    db = SessionLocal()
    try:
        db_rec = db.query(Record).filter(Record.id == record_id).first()
        db_rec.status = "processed"
        db.add(db_rec)
        db.commit()
    finally:
        db.close()

    r2 = client.post(f"/records/{record_id}/process")
    assert r2.status_code == 409
    body = r2.json()
    assert body["error"]["code"] in ("CONFLICT", "ALREADY_PROCESSED")
    assert "request_id" in body or "X-Request-ID" in r2.headers


def test_invalid_payload_returns_422():
    # missing required fields expected by RecordCreate
    r = client.post("/records", json={"subject": "x"})
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in body


def test_summary_on_empty_db_returns_zeroes():
    # Ensure DB is empty
    from workflow_service.app.database import SessionLocal

    db = SessionLocal()
    try:
        db.execute("DELETE FROM records")
        db.commit()
    finally:
        db.close()

    r = client.get("/reports/summary")
    assert r.status_code == 200
    body = r.json()
    assert "totals" in body
    assert body["totals"].get("all", 0) == 0
PY

echo "==> Writing .env.example"
backup_if_exists .env.example
cat > .env.example <<'PY'
DATABASE_URL=sqlite:///./workflow.db
LOG_LEVEL=INFO
PY

echo "==> Writing README.md (appending if exists)"
if [ -f README.md ]; then
  echo "" >> README.md
  echo "## Error response format (Day 6 additions)" >> README.md
else
  cat > README.md <<'PY'
## Error response format
PY
fi

cat >> README.md <<'PY'

All expected errors return a structured JSON body with an `error` object and a `request_id`.

Example:
```json
{
  "error": {
    "code": "RECORD_NOT_FOUND",
    "message": "record not found",
    "details": { "...": "optional details" }
  },
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
