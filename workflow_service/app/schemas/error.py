"""Error response schemas."""

from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Error details."""

    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: ErrorBody
    request_id: str | None = None
