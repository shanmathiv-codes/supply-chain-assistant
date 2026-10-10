"""Schemas for user feedback, outcome tracking, and human review."""
from typing import Literal

from pydantic import BaseModel, Field


class FeedbackSubmission(BaseModel):
    """User submitted feedback on an analysis run."""

    run_id: str
    case_id: str | None = None
    kind: Literal["relevance", "usefulness", "missing_evidence", "incorrect_fact", "general"]
    value: float | str = Field(..., description="Rating (1-5) or category")
    comment: str | None = Field(default=None, max_length=1000)


class OutcomeSubmission(BaseModel):
    """Actual real-world disruption outcome submitted for model evaluation."""

    run_id: str
    actual_production_impact_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    actual_revenue_loss_usd: float | None = Field(default=None, ge=0.0)
    actual_full_recovery_days: float | None = Field(default=None, ge=0.0)
    simulated: bool = False


class FeedbackRecord(BaseModel):
    feedback_id: str
    run_id: str
    case_id: str | None = None
    kind: str
    value: str
    comment: str | None = None
    created_at: str
    status: Literal["pending", "approved", "rejected"] = "pending"
