# Workflow Service Runbook

This runbook provides operational guidance for troubleshooting and maintaining the Workflow Service.

## Table of Contents
- [Common Issues](#common-issues)
- [Security & Authentication](#security--authentication)
- [Monitoring & Logs](#monitoring--logs)
- [Request Tracing](#request-tracing)
- [Local Reproduction](#local-reproduction)
- [Database Operations](#database-operations)
- [Validation with curl](#validation-with-curl)

---

## Common Issues

### Database Connection Errors

**Symptom:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server failed
```

**Root Causes:**
1. DATABASE_URL not set or incorrect
2. Database server not running
3. Network connectivity issues
4. Incorrect credentials

**Resolution Steps:**
1. Verify DATABASE_URL environment variable:
   ```bash
   echo $DATABASE_URL
   ```

2. Test database connectivity:
   ```bash
   # For Postgres
   psql "$DATABASE_URL"

   # For SQLite (check file exists)
   ls -la workflow.db
   ```

3. Check service logs for detailed error:
   ```bash
   # Look for connection details in logs
   grep -i "database" logs/*.log
   ```

4. Verify credentials and permissions:
   - Postgres: Ensure user has CREATE/SELECT/INSERT/UPDATE permissions
   - SQLite: Ensure write permissions on database file and directory

---

### Migration Version Mismatch

**Symptom:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```
or
App queries fail with "table doesn't exist" errors after deployment.

**Root Causes:**
1. Database is behind current code version
2. Migration files missing from deployment
3. Database is ahead of code version (rollback needed)

**Resolution Steps:**
1. Check current migration version:
   ```bash
   cd workflow_service
   alembic current
   ```

2. Check what migrations should be applied:
   ```bash
   alembic history
   ```

3. Apply pending migrations:
   ```bash
   alembic upgrade head
   ```

4. If database is ahead, downgrade to match code:
   ```bash
   # Downgrade one version
   alembic downgrade -1

   # Or downgrade to specific version
   alembic downgrade <revision_id>
   ```

**Prevention:**
- Always run `alembic upgrade head` during deployment
- Include migration files in deployment artifact
- Test migrations in staging before production

---

### 500 Internal Server Errors

**Symptom:**
API returns 500 status with generic error message:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error"
  }
}
```

**Root Causes:**
1. Unhandled exception in business logic
2. Database constraint violation
3. Missing environment variable
4. Data type mismatch

**Resolution Steps:**
1. Check application logs (JSON structured logs):
   ```bash
   # Look for exception traces
   grep '"event":"domain.error"' logs/app.log | tail -20

   # Or for unhandled exceptions
   grep "unhandled exception" logs/app.log | tail -20
   ```

2. Check request_id to trace full request lifecycle:
   ```bash
   grep "request_id\":\"<request_id_here>" logs/app.log
   ```

3. Common fixes:
   - Invalid payload format → Check schema validation
   - Foreign key errors → Verify referenced records exist
   - NULL constraint → Check required fields

---

### Record Processing Failures

**Symptom:**
Records stuck in "pending" status or transition to "failed" status.

**Root Causes:**
1. Invalid payload data
2. Processing service logic error
3. Missing required fields in payload

**Resolution Steps:**
1. Query failed records:
   ```bash
   curl "http://localhost:8000/records?status=failed&limit=10"
   ```

2. Inspect error field:
   ```json
   {
     "id": "...",
     "status": "failed",
     "error": "classification failed: invalid payload format"
   }
   ```

3. Verify payload structure matches expected format:
   ```bash
   # Get specific failed record
   curl http://localhost:8000/records/<record_id>
   ```

4. Re-process after fixing payload (if applicable):
   ```bash
   # Note: Current implementation doesn't support re-processing failed records
   # Manual intervention needed: update status to pending, then process
   ```

---

## Security & Authentication

### API Key Authentication

Write operations (POST, PUT, PATCH, DELETE) are protected by API key authentication.

**How to validate auth is working:**

1. **Check if API key is configured:**
   ```bash
   echo $API_KEY
   # If empty, auth is disabled (dev mode)
   # If set, auth is enabled (production mode)
   ```

2. **Test without API key (should fail if API_KEY is set):**
   ```bash
   curl -X POST http://localhost:8000/records \
     -H "Content-Type: application/json" \
     -d '{"source": "test", "category": "test", "payload": {}}'

   # Expected response if auth enabled:
   # {
   #   "error": {
   #     "code": "UNAUTHORIZED",
   #     "message": "API key required"
   #   },
   #   "request_id": "..."
   # }
   ```

3. **Test with correct API key (should succeed):**
   ```bash
   curl -X POST http://localhost:8000/records \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"source": "test", "category": "test", "payload": {}}'

   # Expected: 201 Created
   ```

4. **Test with wrong API key (should fail):**
   ```bash
   curl -X POST http://localhost:8000/records \
     -H "Content-Type: application/json" \
     -H "X-API-Key: wrong-key" \
     -d '{"source": "test", "category": "test", "payload": {}}'

   # Expected response:
   # {
   #   "error": {
   #     "code": "UNAUTHORIZED",
   #     "message": "Invalid API key"
   #   },
   #   "request_id": "..."
   # }
   ```

**Common auth failure symptoms:**

1. **401 Unauthorized - Missing API key**
   - Symptom: Write operations fail with "API key required"
   - Fix: Include `X-API-Key` header with valid key

2. **401 Unauthorized - Invalid API key**
   - Symptom: Write operations fail with "Invalid API key"
   - Fix: Verify `API_KEY` environment variable matches header value

3. **Auth works locally but fails in production**
   - Symptom: Local writes succeed, production writes fail
   - Fix: Ensure `API_KEY` is set in production environment

**Generating a secure API key:**
```bash
# Generate a cryptographically secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# vK3pL9mN2xQ8wR7tY6uI5oP4sA1dF0gH3jK2lZ9nM8bV
```

---

## Monitoring & Logs

### Log Format
The service outputs structured JSON logs to stdout:

```json
{
  "event": "request.end",
  "method": "POST",
  "path": "/records",
  "status_code": 201,
  "duration_ms": 42,
  "request_id": "abc-123-def"
}
```

### Key Log Events
- `request.start` - Incoming request
- `request.end` - Request completed
- `domain.error` - Business logic error
- `validation.error` - Request validation failed
- `http.error` - HTTP exception (4xx/5xx)
- `unhandled exception` - Unexpected error (Python traceback follows)

### Log Locations
- **Local dev:** stdout (console)
- **Docker:** `docker logs <container_id>`
- **Production:** Depends on deployment (CloudWatch, Datadog, etc.)

### Useful Log Queries

```bash
# Find slow requests (>1000ms)
grep '"duration_ms"' logs/app.log | jq 'select(.duration_ms > 1000)'

# Count errors by type
grep '"event":"domain.error"' logs/app.log | jq -r '.error.code' | sort | uniq -c

# Track specific request flow
grep '"request_id":"<id>"' logs/app.log | jq .
```

---

## Request Tracing

### How to use request_id to trace issues

Every request is assigned a unique `request_id` that flows through the entire request lifecycle, making it easy to trace a single request from start to finish.

**1. Obtain the request_id from the response:**

Every API response includes the `X-Request-ID` header:
```bash
curl -i http://localhost:8000/records

# Response headers will include:
# X-Request-ID: 7f3a4b2c-8d9e-4f1a-b2c3-d4e5f6a7b8c9
```

Error responses include `request_id` in the JSON body:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "record not found"
  },
  "request_id": "7f3a4b2c-8d9e-4f1a-b2c3-d4e5f6a7b8c9"
}
```

**2. Provide your own request_id for tracking:**

You can send a custom request ID to make tracing easier:
```bash
curl -H "X-Request-ID: my-debug-request-001" http://localhost:8000/records
```

The same ID will be used in all logs and returned in the response.

**3. Trace a request through logs:**

Using the `request_id`, find all log entries for that request:

```bash
# View all events for a specific request
grep '"request_id":"7f3a4b2c-8d9e-4f1a-b2c3-d4e5f6a7b8c9"' logs/app.log | jq .

# Example output shows the full request lifecycle:
# {"event":"request.start","method":"POST","path":"/records","request_id":"7f3a..."}
# {"event":"request.end","method":"POST","path":"/records","status_code":201,"duration_ms":45,"request_id":"7f3a..."}
```

**4. Troubleshoot errors with request_id:**

When a user reports an error, ask for the `request_id` from the error response:

```bash
# Find the error details
grep '"request_id":"<request_id>"' logs/app.log | jq 'select(.event == "http.error" or .event == "domain.error")'

# Look for exceptions
grep '"request_id":"<request_id>"' logs/app.log | grep -A 10 "unhandled exception"
```

**5. Correlate multiple requests:**

For batch operations or workflows, use custom `X-Request-ID` with a common prefix:
```bash
# Upload batch with related IDs
curl -H "X-Request-ID: batch-001-item-1" ...
curl -H "X-Request-ID: batch-001-item-2" ...
curl -H "X-Request-ID: batch-001-item-3" ...

# Find all related requests
grep '"request_id":"batch-001-' logs/app.log | jq .
```

**Best practices:**
- Always capture `request_id` from error responses before reporting issues
- Use custom request IDs for debugging sessions (e.g., `debug-yourname-001`)
- Include request_id in support tickets
- Monitor logs in real-time during troubleshooting:
  ```bash
  tail -f logs/app.log | grep '"request_id":"<id>"' | jq .
  ```

---

## Local Reproduction

### Prerequisites
```bash
python --version  # Requires Python 3.10+
```

### Setup Steps
1. Clone repository and create virtual environment:
   ```bash
   git clone <repo_url>
   cd new_job_project
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   cd workflow_service
   pip install -r requirements.txt
   ```

3. Set up environment (optional for SQLite):
   ```bash
   cp ../.env.example .env
   # Edit .env if needed
   ```

4. Run migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the service:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. Verify service is running:
   ```bash
   curl http://localhost:8000/health
   ```

### Reproduce Production Issue

1. Check production logs for request_id
2. Extract request payload from logs
3. Replay request locally:
   ```bash
   curl -X POST http://localhost:8000/records \
     -H "Content-Type: application/json" \
     -d '<payload_from_logs>'
   ```

4. Examine local logs and behavior
5. Add breakpoints or debug prints as needed

---

## Database Operations

### Create Migration
```bash
cd workflow_service
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migration
```bash
alembic upgrade head
```

### Rollback Migration
```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Reset Database (Dev Only)
```bash
# SQLite
rm workflow.db
alembic upgrade head

# Postgres
psql -c "DROP DATABASE workflow_db;"
psql -c "CREATE DATABASE workflow_db;"
alembic upgrade head
```

### View Migration History
```bash
alembic history --verbose
```

### Check Current Version
```bash
alembic current
```

---

## Validation with curl

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Create Record
```bash
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "category": "test",
    "payload": {"key": "value"}
  }'
# Expected: 201 with record JSON
```

### List Records (with sorting)
```bash
# Default (newest first)
curl "http://localhost:8000/records"

# Sort by status ascending
curl "http://localhost:8000/records?sort_by=status&sort_order=asc"

# Filter and paginate
curl "http://localhost:8000/records?status=pending&limit=10&offset=0"
```

### Get Specific Record
```bash
curl http://localhost:8000/records/<record_id>
# Expected: 200 with record JSON
```

### Process Record
```bash
curl -X POST http://localhost:8000/records/<record_id>/process
# Expected: 200 with updated record (status=processed or failed)
```

### Get Summary Report
```bash
curl "http://localhost:8000/reports/summary"
# Expected: JSON with totals by status and category
```

### Test Error Handling
```bash
# Invalid payload (should return 422)
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{"invalid": "payload"}'

# Non-existent record (should return 404)
curl http://localhost:8000/records/non-existent-id

# Invalid sort parameter (should return 422)
curl "http://localhost:8000/records?sort_by=invalid"
```

---

## Emergency Procedures

### Service Won't Start
1. Check if port is already in use:
   ```bash
   lsof -i :8000  # Unix
   netstat -ano | findstr :8000  # Windows
   ```

2. Verify database connectivity before starting app
3. Check for syntax errors:
   ```bash
   python -m py_compile app/main.py
   ```

### Database Corruption (SQLite)
```bash
# Check integrity
sqlite3 workflow.db "PRAGMA integrity_check;"

# If corrupted, restore from backup or recreate
rm workflow.db
alembic upgrade head
```

### High Memory Usage
1. Check connection pool settings in [database.py](../workflow_service/app/database.py)
2. Monitor active database connections
3. Consider adding connection limits

### Performance Degradation
1. Check for missing indexes on frequently queried fields
2. Monitor slow query logs
3. Consider adding indexes in migration:
   ```python
   # In migration file
   op.create_index('idx_records_status', 'records', ['status'])
   op.create_index('idx_records_created_at', 'records', ['created_at'])
   ```

---

## Support Contacts

- **On-call Engineer:** [Your team's on-call rotation]
- **Database Team:** [DBA contact if applicable]
- **Deployment/DevOps:** [Platform team contact]

## Additional Resources

- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI
- [Main README](../README.md) - Project overview and setup
- [Architecture Docs](./architecture.md) - System design (if exists)
