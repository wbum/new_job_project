"""Domain exceptions for consistent error handling."""


class DomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        status_code: int = 400,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(DomainError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(message, code="NOT_FOUND", status_code=404, details=details)


class ConflictError(DomainError):
    """Resource conflict (e.g., duplicate, invalid state transition)."""

    def __init__(self, message: str = "Resource conflict", details: dict | None = None):
        super().__init__(message, code="CONFLICT", status_code=409, details=details)


class ValidationError(DomainError):
    """Domain validation error."""

    def __init__(self, message: str = "Validation error", details: dict | None = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400, details=details)
