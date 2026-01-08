import json
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from .api import (
    health,  # existing
    records,
    reports,  # existing
)
from .database import Base, engine
from .exceptions import DomainError
from .schemas.error import ErrorBody, ErrorResponse

APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# configure a service logger; we will log structured JSON strings to stdout
logger = logging.getLogger("workflow_service")
# Avoid adding duplicate handlers if module is imported more than once
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
# Prevent double-logging via propagation to root handlers
logger.propagate = False
logger.setLevel(LOG_LEVEL)


def _log_json(obj: dict, level: str = "info"):
    try:
        payload = json.dumps(obj, default=str)
    except Exception:
        payload = json.dumps({"msg": "failed to serialize log object"})
    getattr(logger, level)(payload)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        started_at = time.time()
        # support X-Request-ID header propagation
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        _log_json(
            {
                "event": "request.start",
                "method": request.method,
                "path": request.url.path,
                "request_id": request_id,
            },
            level="info",
        )

        try:
            response = await call_next(request)
        except Exception:
            # Let global exception handlers deal with it; re-raise to ensure they run
            raise

        duration_ms = int((time.time() - started_at) * 1000)

        _log_json(
            {
                "event": "request.end",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
            level="info",
        )
        # attach request id header back to client
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(title="Workflow Service", version=APP_VERSION)

# Development convenience: create tables if missing
Base.metadata.create_all(bind=engine)

# CORS configuration - restrict to known origins in production
# For local dev, allow localhost. For production, set ALLOWED_ORIGINS env var
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(
    ","
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# add logging middleware and exception handlers
app.add_middleware(RequestLoggingMiddleware)

# include routers
app.include_router(health.router)
app.include_router(records.router)
app.include_router(reports.router)


# Root endpoint - provides service info and links
@app.get("/")
def root():
    """
    Root endpoint that provides service information and available endpoints.
    """
    return {
        "service": "workflow_service",
        "version": APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "records": "/records",
            "reports": "/reports/summary",
        },
    }


# Exception handlers: domain errors -> structured JSON
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    request_id = getattr(request.state, "request_id", None)
    body = ErrorResponse(
        error=ErrorBody(
            code=getattr(exc, "code", "DOMAIN_ERROR"),
            message=str(exc.message),
            details=getattr(exc, "details", None),
        ),
        request_id=request_id,
    ).dict()
    # log with stackless context
    _log_json(
        {"event": "domain.error", "error": body["error"], "request_id": request_id}, level="warning"
    )
    return JSONResponse(status_code=getattr(exc, "status_code", 400), content=body)


# Pydantic/validation errors -> standardized 422 body
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    details = exc.errors()
    body = ErrorResponse(
        error=ErrorBody(code="VALIDATION_ERROR", message="Validation failed", details=details),
        request_id=request_id,
    ).dict()
    _log_json(
        {"event": "validation.error", "details": details, "request_id": request_id}, level="warning"
    )
    return JSONResponse(status_code=422, content=body)


# catch-all for unexpected errors -> 500 but safe response
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    # log full stack trace for server-side investigation
    logger.exception("unhandled exception (request_id=%s)", request_id)
    body = ErrorResponse(
        error=ErrorBody(code="INTERNAL_ERROR", message="Internal server error"),
        request_id=request_id,
    ).dict()
    return JSONResponse(status_code=500, content=body)
