"""Standard error payload and response models."""
from typing import Any, Literal

from pydantic import BaseModel, Field

ErrorCode = Literal[
    "VALIDATION_ERROR",
    "INJECTION_SUSPECTED",
    "OFF_TOPIC",
    "SUBSTRATE_UNAVAILABLE",
    "NO_EVIDENCE",
    "LLM_UNAVAILABLE",
    "RATE_LIMITED",
    "INTERNAL",
    "UNAUTHORIZED",
    "NOT_FOUND",
]


class ErrorDetail(BaseModel):
    code: ErrorCode = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    details: Any = Field(default=None, description="Optional diagnostic details or validation errors")


class ErrorResponse(BaseModel):
    error: ErrorDetail
