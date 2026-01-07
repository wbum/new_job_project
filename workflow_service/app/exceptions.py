"""
Domain exceptions and error response utilities for the workflow service.
"""
from typing import Any, Dict, Optional


class DomainError(Exception):
    """Base exception for domain-specific errors."""
    
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(DomainError):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message: str = "resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(code="RECORD_NOT_FOUND", message=message, details=details)


class ConflictError(DomainError):
    """Exception raised when an operation conflicts with current resource state."""
    
    def __init__(self, message: str = "resource conflict", code: str = "ALREADY_PROCESSED", details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, details=details)


def create_error_response(
    code: str,
    message: str,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        code: Error code (e.g., RECORD_NOT_FOUND, VALIDATION_ERROR)
        message: Human-readable error message
        request_id: Request ID if available
        details: Optional additional error details
    
    Returns:
        Dictionary with standardized error structure
    """
    response: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    if request_id:
        response["request_id"] = request_id
    
    return response
