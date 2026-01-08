"""Security utilities for API key authentication."""

from fastapi import Header, HTTPException, status

from ..config import settings


def verify_api_key(x_api_key: str = Header(None)) -> str:
    """
    Verify API key for write operations.

    Reads from header: X-API-Key
    Returns the key if valid, raises 401 if missing or invalid.
    """
    if not settings.API_KEY:
        # No API key configured = open access (dev mode)
        return "dev-mode"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key
