# Workflow Automation & Reporting API

Status: Production-ready

A production-ready FastAPI backend for workflow automation that ingests records, persists them with PostgreSQL or SQLite, processes them through explicit state transitions (pending → processed/failed), and exposes operational reporting with filtering, pagination, and sorting.

## Live Deployment

**Production URL:** [Your deployment URL here]
- **API Documentation:** [Your URL]/docs
- **Health Check:** [Your URL]/health
- **OpenAPI Spec:** [Your URL]/openapi.json

## Tech Stack
- **Framework:** Python 3.10+, FastAPI, Uvicorn
- **Database:** PostgreSQL (production) / SQLite (local dev)
- **ORM:** SQLAlchemy with Alembic migrations
- **Validation:** Pydantic v2
- **Testing:** pytest with coverage
- **Code Quality:** ruff, black

## Features
- Health check endpoint with monitoring support
- RESTful record management (create, retrieve, list)
- Stateful processing with idempotency guarantees
- Advanced querying: filtering, pagination, sorting
- Summary reporting with aggregations
- Structured JSON logging with request tracking
- Database migrations with Alembic
- PostgreSQL and SQLite support
- Production-ready error handling and validation
- Comprehensive test coverage

## Quick Start

### Prerequisites
- Python 3.10 or higher
- PostgreSQL (for production) or SQLite (auto-created for dev)

### 1) Clone and Set Up Environment
```bash
git clone <repository_url>
cd new_job_project
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2) Install Dependencies
```bash
cd workflow_service
pip install -r requirements.txt
```

### 3) Configure Environment (Optional)
For local development with SQLite, no configuration needed. The app uses SQLite by default.

For PostgreSQL:
```bash
# Copy example env file
cp .env.example .env

# Edit .env and set:
# DATABASE_URL=postgresql://user:password@localhost:5432/workflow_db
```

### 4) Run Database Migrations
```bash
# Apply all migrations to create database schema
alembic upgrade head
```

### 5) Start the Server
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6) Verify Installation
```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# View API docs
open http://localhost:8000/docs  # macOS
# Or visit http://localhost:8000/docs in your browser
```

## Running Tests

```bash
cd workflow_service

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_processing.py

# Run with verbose output
pytest -v
```

## Database Operations

### Creating Migrations
When you modify database models:
```bash
cd workflow_service
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Applying Migrations
```bash
alembic upgrade head
```

### Rolling Back Migrations
```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>
```

### Reset Database (Dev Only)
```bash
# SQLite
rm workflow.db
alembic upgrade head

# PostgreSQL
psql -c "DROP DATABASE workflow_db;"
psql -c "CREATE DATABASE workflow_db;"
alembic upgrade head
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./workflow.db` | Database connection string |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `APP_ENV` | `dev` | Environment (dev, staging, prod) |
| `PROJECT_NAME` | `workflow_service` | Project name for logging |
| `APP_VERSION` | `0.1.0` | Application version |

### Database URLs

**SQLite (local dev):**
```bash
DATABASE_URL=sqlite:///./workflow.db
```

**PostgreSQL (production):**
```bash
DATABASE_URL=postgresql://username:password@host:port/database_name

# Example with connection pooling params
DATABASE_URL=postgresql://user:pass@db.example.com:5432/workflow_db?pool_size=10&max_overflow=20
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status.

### Records

**Create Record**
```bash
POST /records
Content-Type: application/json

{
  "source": "api",
  "category": "analytics",
  "payload": {"user_id": 123, "action": "click"}
}
```

**List Records** (with filtering, pagination, sorting)
```bash
GET /records?status=pending&limit=10&offset=0&sort_by=created_at&sort_order=desc
```

Query parameters:
- `status`: Filter by status (pending, processed, failed)
- `category`: Filter by category
- `created_after`: ISO datetime (e.g., 2024-01-01T00:00:00Z)
- `created_before`: ISO datetime
- `limit`: Results per page (default: 50, max: 200)
- `offset`: Number of results to skip (default: 0)
- `sort_by`: Sort field (created_at, status, category, source)
- `sort_order`: Sort direction (asc, desc)

**Get Record**
```bash
GET /records/{record_id}
```

**Process Record**
```bash
POST /records/{record_id}/process
```

### Reports

**Get Summary**
```bash
GET /reports/summary?status=processed&date_from=2024-01-01
```

Returns aggregated counts by status and category.

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t workflow-service:latest .

# Run with SQLite
docker run -p 8000:8000 workflow-service:latest

# Run with PostgreSQL
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/workflow_db \
  workflow-service:latest
```

### Docker Compose

```bash
docker-compose up -d
```

This starts the service with all dependencies.

### Production Deployment Checklist

1. **Set Environment Variables**
   ```bash
   export DATABASE_URL=postgresql://user:pass@prod-db:5432/workflow_db
   export APP_ENV=prod
   export LOG_LEVEL=INFO
   ```

2. **Run Migrations**
   ```bash
   cd workflow_service
   alembic upgrade head
   ```

3. **Start Service**
   ```bash
   # With multiple workers for production
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

   # Or use gunicorn with uvicorn workers
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

4. **Verify Deployment**
   ```bash
   curl https://your-domain.com/health
   curl https://your-domain.com/docs
   ```

## Troubleshooting

For detailed troubleshooting guidance, see [docs/runbook.md](docs/runbook.md).

Common issues:
- **Database connection errors**: Verify DATABASE_URL and database accessibility
- **Migration errors**: Check `alembic current` vs `alembic history`
- **500 errors**: Check application logs for stack traces
- **Performance issues**: Monitor database connection pool and query performance

## Project Structure

```
new_job_project/
├── workflow_service/           # Main application
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # Database setup
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── main.py            # FastAPI application
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Test suite
│   └── requirements.txt       # Python dependencies
├── docs/
│   └── runbook.md             # Operational runbook
├── .env.example               # Environment variables template
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local development stack
└── README.md                  # This file
```

## Development

### Code Style
```bash
# Format code
black workflow_service/

# Lint code
ruff check workflow_service/

# Auto-fix linting issues
ruff check --fix workflow_service/
```

### Adding New Endpoints
1. Create route handler in `app/api/`
2. Add business logic to `app/services/`
3. Update schemas in `app/schemas/` if needed
4. Write tests in `tests/`
5. Update API documentation (auto-generated from docstrings)

### Database Schema Changes
1. Modify models in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration file if needed
4. Apply migration: `alembic upgrade head`
5. Test rollback: `alembic downgrade -1` then `alembic upgrade head`

## Contributing

1. Create a feature branch from `main`
2. Make changes with tests
3. Ensure tests pass: `pytest`
4. Format code: `black .` and `ruff check --fix .`
5. Create pull request

## License

[Your license here]

## Support

- **Documentation**: See `/docs` endpoint when service is running
- **Issues**: [GitHub Issues](https://github.com/your-org/your-repo/issues)
- **Runbook**: [docs/runbook.md](docs/runbook.md)
