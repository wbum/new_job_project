"""Error response schemas."""

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Error details."""

    code: str
    message: str
    details: Any = None  # Can be dict, list, or None depending on error type


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: ErrorBody
    request_id: str | None = None
