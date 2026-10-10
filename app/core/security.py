"""Security helpers, API key verification, and redaction utilities."""
from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> bool:
    """Validate optional API key header against configured API_KEY setting."""
    if not settings.api_key:
        return True  # Auth not enforced if API_KEY unset

    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing API key in X-API-Key header",
                }
            },
        )
    return True
