# Workflow Service

[![CI](https://github.com/YOUR_USERNAME/new_job_project/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/new_job_project/actions/workflows/ci.yml)

A production-ready FastAPI service for workflow automation with state transitions, idempotency, and comprehensive error handling.

## Project Highlights

- **State Machine**: Records transition through `pending → processed/failed` states with validation
- **Idempotency**: Conflict detection prevents duplicate processing (409 on retry)
- **Structured Errors**: Consistent error schema with request IDs for traceability
- **Request Logging**: Every request logged with unique `request_id` for debugging
- **Production-Ready**: Docker support, CI/CD, linting, formatting, and health checks

## Quick Start

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r workflow_service/requirements.txt

# Run the service
cd workflow_service
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## Documentation

For detailed API documentation, examples, and development guide, see [workflow_service/README.md](workflow_service/README.md)

## Example Usage

```bash
# Create a record
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{"source":"api","category":"order","payload":{"order_id":"12345","amount":99.99}}'

# Process the record
curl -X POST http://localhost:8000/records/<record-id>/process

# Get summary report
curl http://localhost:8000/reports/summary
```

## Docker

```bash
# Build and run
docker build -t workflow-service .
docker run -p 8000:8000 workflow-service

# Or use docker-compose
docker-compose up
```

## Development

```bash
# Format code
black .

# Lint code
ruff check .

# Run tests
pytest --cov=workflow_service
```

## License

MIT
