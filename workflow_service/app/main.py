import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api import records
from .api import health  # existing
from .api import reports  # new
from .database import engine, Base
from .exceptions import DomainError, NotFoundError, ConflictError, create_error_response

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("workflow")

app = FastAPI(title="Workflow Service", version="0.1.0")

# Development convenience: create tables if missing
Base.metadata.create_all(bind=engine)


# Middleware for request ID and structured logging
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Callable):
    """Add request ID to request state and response headers, log requests."""
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    # Record start time
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    # Log structured request info
    logger.info(
        f"request_id={request_id} method={request.method} path={request.url.path} "
        f"status_code={response.status_code} duration_ms={duration_ms:.2f}"
    )
    
    return response


# Exception handlers
@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle NotFoundError exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"request_id={request_id} error_code={exc.code} message={exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details
        )
    )


@app.exception_handler(ConflictError)
async def conflict_error_handler(request: Request, exc: ConflictError):
    """Handle ConflictError exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"request_id={request_id} error_code={exc.code} message={exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details
        )
    )


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Handle generic DomainError exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"request_id={request_id} error_code={exc.code} message={exc.message}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details
        )
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"request_id={request_id} validation_error errors={exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            code="VALIDATION_ERROR",
            message="request validation failed",
            request_id=request_id,
            details={"errors": exc.errors()}
        )
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception(f"request_id={request_id} unhandled_exception={type(exc).__name__}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code="INTERNAL_ERROR",
            message="internal server error",
            request_id=request_id
        )
    )


app.include_router(health.router)
app.include_router(records.router)
app.include_router(reports.router)
