# new_job_project
Project for a new possible job.

## API Examples

### Create a Record

Create a new record with workflow processing:

```bash
curl -X POST http://localhost:8000/records \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api",
    "category": "attendance",
    "payload": {
      "subject": "Employee Check-in",
      "metrics": {
        "severity": 7,
        "impact": 6,
        "urgency": 2
      }
    }
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### Get a Record

Retrieve details of a specific record:

```bash
curl -X GET http://localhost:8000/records/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "subject": "Employee Check-in",
    "metrics": {
      "severity": 7,
      "impact": 6,
      "urgency": 2
    }
  },
  "status": "processed",
  "classification": "low",
  "score": 0.0,
  "error": null
}
```

### Process a Record

Manually trigger processing for a record:

```bash
curl -X POST http://localhost:8000/records/550e8400-e29b-41d4-a716-446655440000/process
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### Get Summary Report

Get aggregated summary statistics:

```bash
curl -X GET http://localhost:8000/reports/summary
```

Response:
```json
{
  "generated_at": "2026-01-05T00:00:00.000Z",
  "filters": {
    "status": null,
    "category": null,
    "date_from": null,
    "date_to": null
  },
  "totals": {
    "all": 100,
    "pending": 10,
    "processed": 85,
    "failed": 5
  },
  "by_category": [
    {
      "category": "attendance",
      "count": 45
    },
    {
      "category": "payroll",
      "count": 35
    },
    {
      "category": "hr",
      "count": 20
    }
  ]
}
```

### Get Filtered Summary Report

Get summary with filters applied:

```bash
curl -X GET "http://localhost:8000/reports/summary?status=processed&category=attendance&date_from=2026-01-01T00:00:00Z&date_to=2026-01-05T23:59:59Z"
```

Response:
```json
{
  "generated_at": "2026-01-05T00:00:00.000Z",
  "filters": {
    "status": "processed",
    "category": "attendance",
    "date_from": "2026-01-01T00:00:00Z",
    "date_to": "2026-01-05T23:59:59Z"
  },
  "totals": {
    "all": 40,
    "pending": 0,
    "processed": 40,
    "failed": 0
  },
  "by_category": [
    {
      "category": "attendance",
      "count": 40
    }
  ]
}
```

### List Records with Pagination

List all records with pagination:

```bash
curl -X GET "http://localhost:8000/records?limit=10&offset=0"
```

Response:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-01-05T00:00:00.000Z",
      "status": "processed",
      "source": "api",
      "category": "attendance",
      "payload": {
        "subject": "Employee Check-in"
      },
      "classification": "low",
      "score": 0.0,
      "error": null
    }
  ],
  "total": 100,
  "limit": 10,
  "offset": 0
}
```

### List Records with Filters

List records with status and category filters:

```bash
curl -X GET "http://localhost:8000/records?status=processed&category=attendance&limit=50&offset=0"
```

Response:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-01-05T00:00:00.000Z",
      "status": "processed",
      "source": "api",
      "category": "attendance",
      "payload": {
        "subject": "Employee Check-in"
      },
      "classification": "low",
      "score": 0.0,
      "error": null
    }
  ],
  "total": 45,
  "limit": 50,
  "offset": 0
}
```
