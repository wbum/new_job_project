# new_job_project
# Workflow Automation & Reporting API

Status: Active development

A FastAPI backend that ingests records, persists them to SQLite via SQLAlchemy, processes them through explicit state transitions (pending → processed/failed), and exposes operational reporting (summary counts by status/category).

## Tech Stack
- Python, FastAPI, Uvicorn
- SQLite, SQLAlchemy
- Pydantic (validation)
- pytest (tests)

## Features
- Health check endpoint
- Create and retrieve records
- Stateful processing with idempotency (re-process returns a conflict)
- Summary reporting (counts by status/category) + basic filters
- Test coverage for processing logic and failure modes

## Quick Start

### 1) Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
