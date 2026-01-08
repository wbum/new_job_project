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

## Live Demo

**🚀 Try it live:** The API is deployed and ready to explore!

- **Base URL**: `https://new-job-project.onrender.com/`
- **Interactive API Docs**: `https://new-job-project.onrender.com/docs`
- **Health Check**: `https://new-job-project.onrender.com/health`

### Live Examples

```bash
# Check service health
curl https://new-job-project.onrender.com/health

# Create a record
curl -X POST https://new-job-project.onrender.com/records \
  -H "Content-Type: application/json" \
  -d '{"source":"demo","category":"example","payload":{"message":"Hello from live demo!"}}'

# Get summary report
curl https://new-job-project.onrender.com/reports/summary
```

**Note**: The free tier may take 30-60 seconds to wake up from sleep on first request.

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
