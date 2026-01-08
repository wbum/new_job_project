# Workflow Service

[![CI](https://github.com/wbum/new_job_project/actions/workflows/ci.yml/badge.svg)](https://github.com/wbum/new_job_project/actions/workflows/ci.yml)

A production-ready FastAPI service for workflow automation with state transitions, idempotency, and comprehensive error handling.

## Project Highlights

- **State Machine**: Records transition through `pending → processed/failed` states with validation
- **Idempotency**: Conflict detection prevents duplicate processing (409 on retry)
- **Structured Errors**: Consistent error schema with request IDs for traceability
- **Request Logging**: Every request logged with unique `request_id` for debugging
- **Production-Ready**: Docker support, CI/CD, linting, formatting, and health checks

## Quick Start

### Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the service
cd workflow_service
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

### Docker

```bash
# Build and run with Docker
docker build -t workflow-service .
docker run -p 8000:8000 workflow-service

# Or use docker-compose for development
docker-compose up
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Create Record
```bash
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "category": "order",
    "payload": {"order_id": "12345", "amount": 99.99}
  }'
```

**Success Response (201)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-07T12:00:00",
  "status": "pending",
  "source": "api",
  "category": "order",
  "payload": {"order_id": "12345", "amount": 99.99},
  "classification": null,
  "score": null,
  "error": null
}
```

### Process Record
```bash
curl -X POST http://localhost:8000/records/550e8400-e29b-41d4-a716-446655440000/process
```

**Success Response (200)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processed",
  "classification": "high_value",
  "score": "0.95"
}
```

**Conflict Response (409)** - Already processed:
```json
{
  "error": "Conflict",
  "message": "Record already processed",
  "request_id": "req_abc123"
}
```

### Get Record
```bash
curl http://localhost:8000/records/550e8400-e29b-41d4-a716-446655440000
```

**Not Found Response (404)**:
```json
{
  "error": "NotFound",
  "message": "Record not found",
  "request_id": "req_xyz789"
}
```

### List Records (with filtering)
```bash
# Get all records
curl http://localhost:8000/records

# Filter by status
curl "http://localhost:8000/records?status=processed"

# Filter by category and limit results
curl "http://localhost:8000/records?category=order&limit=10"
```

### Get Summary Report
```bash
curl http://localhost:8000/reports/summary
```

**Response**:
```json
{
  "total_records": 150,
  "by_status": {
    "pending": 20,
    "processed": 120,
    "failed": 10
  },
  "by_category": {
    "order": 100,
    "refund": 50
  }
}
```

## Development

### Code Quality

Format code:
```bash
black .
```

Lint code:
```bash
ruff check .
```

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=workflow_service --cov-report=term-missing
```

### Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Configuration options:
- `DATABASE_URL`: Database connection string (default: SQLite)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `APP_ENV`: Environment name (dev, staging, prod)

## CI/CD

GitHub Actions workflow runs on every push and PR:
- ✅ Install dependencies
- ✅ Run ruff linter
- ✅ Run black formatter check
- ✅ Run tests with coverage

A failing test or linting error will block the merge.

## Architecture

```
workflow_service/
├── app/
│   ├── main.py              # FastAPI app + middleware
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # Database models
│   │   └── record.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   └── record.py
│   ├── api/                 # Route handlers
│   │   ├── health.py
│   │   ├── records.py
│   │   └── reports.py
│   ├── services/            # Business logic
│   │   ├── processing.py
│   │   └── reporting.py
│   └── utils/
│       └── logging.py
└── tests/                   # Test suite
```

## License

MIT
