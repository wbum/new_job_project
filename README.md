# Workflow Automation & Reporting API

Status: Active development

A FastAPI backend that ingests records, persists them to SQLite via SQLAlchemy, processes them through explicit state transitions (pending → processed/failed), and exposes operational reporting (summary counts by status/category).

## Tech Stack
- Python, FastAPI, Uvicorn
- SQLite, SQLAlchemy
- Pydantic (validation)
- pytest (tests)

## Features
- Health check endpoint with database connectivity check
- Create and retrieve records
- Stateful processing with idempotency (re-process returns a conflict)
- Summary reporting (counts by status/category) + basic filters
- Production-ready error handling with structured responses
- Request ID tracking (X-Request-ID header)
- Structured logging for all requests and state transitions
- Test coverage for processing logic and failure modes

## Quick Start

### 1) Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

### 2) Install dependencies
```bash
pip install -r workflow_service/requirements.txt
```

### 3) Configure environment (optional)
```bash
cp .env.example .env
# Edit .env to customize DATABASE_URL, LOG_LEVEL, etc.
```

### 4) Run the service
```bash
cd workflow_service
uvicorn app.main:app --reload
```

The service will be available at http://localhost:8000

### 5) Run tests
```bash
PYTHONPATH='.' LOG_LEVEL=INFO python3 -m pytest -v
```

## API Documentation

### State Transitions

Records follow a strict state machine:
- **pending** → **processed** (successful processing)
- **pending** → **failed** (processing error)
- Attempting to process a non-pending record returns a 409 Conflict error

### Error Response Format

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {} 
  },
  "request_id": "uuid4-request-identifier"
}
```

#### Error Codes
- `RECORD_NOT_FOUND` - Resource does not exist (404)
- `ALREADY_PROCESSED` - Record is not in pending state (409)
- `VALIDATION_ERROR` - Request validation failed (422)
- `INTERNAL_ERROR` - Unexpected server error (500)

### Request ID Tracking

Every request and response includes an `X-Request-ID` header for correlation:
- If the client provides `X-Request-ID`, it will be echoed back
- If not provided, the server generates a UUID4
- The request ID is included in all log entries and error responses

## API Examples

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "service": "ok",
  "version": "0.1.0",
  "database": {
    "status": "ok"
  }
}
```

### Create a Record
```bash
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-custom-id" \
  -d '{
    "source": "api",
    "category": "attendance",
    "payload": {"name": "Alice", "priority": 3}
  }'
```

### Process a Record
```bash
curl -X POST http://localhost:8000/records/{record_id}/process
```

### Conflict Scenario (Re-processing)
```bash
# First process - succeeds
curl -X POST http://localhost:8000/records/{record_id}/process

# Second process - returns 409 Conflict
curl -X POST http://localhost:8000/records/{record_id}/process
```

Response:
```json
{
  "error": {
    "code": "ALREADY_PROCESSED",
    "message": "record is not pending"
  },
  "request_id": "uuid4-value"
}
```

### Get Summary Report
```bash
curl http://localhost:8000/reports/summary?status=processed&category=attendance
```

## Logging

The service emits structured logs for all requests:
- Request method, path, status code, and duration
- Record state transitions with old/new status
- Error conditions with request IDs for correlation

Example log entry:
```
2026-01-07 12:34:56,789 - workflow - INFO - request_id=abc-123 method=POST path=/records/xyz/process status_code=200 duration_ms=45.23
```

## Development

### Project Structure
```
workflow_service/
  app/
    api/          # API endpoints
    models/       # Database models
    schemas/      # Pydantic schemas
    services/     # Business logic
    exceptions.py # Custom exceptions
    main.py       # FastAPI app with middleware and handlers
  tests/          # Test suite
```

### Adding New Features
1. Define domain exceptions in `exceptions.py`
2. Implement business logic in `services/`
3. Add API endpoints in `api/`
4. Write tests in `tests/`
5. Update this README

## License
MIT
