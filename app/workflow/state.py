"""Typed workflow state dictionary conforming to LangGraph specifications."""

from typing import Any, Literal

from typing_extensions import TypedDict

from app.schemas.evidence import Evidence, SubstrateCall
from app.schemas.report import (
    AskLaneResult,
    Claim,
    ClassificationResult,
    Prediction,
    PriorityAssessment,
    Recommendation,
    Report,
    ResilienceEstimate,
    SimilarCase,
)
from app.schemas.request import DisruptionAnalyzeRequest


class WorkflowState(TypedDict, total=False):
    """Complete serializable state container for disruption analysis workflow."""

    run_id: str
    runtime_modes: dict[str, str]
    request: DisruptionAnalyzeRequest
    profile: dict[str, Any]
    free_text: str
    missing_fields: list[str]

    # Classification
    classification: ClassificationResult | None

    # Substrate & Retrieval
    similar_cases: list[SimilarCase]
    evidence: dict[str, Evidence]
    substrate_trace: list[SubstrateCall]
    ask_lane: AskLaneResult | None
    lane_overlap: float
    relaxed_filters: list[str]

    # Quantitative Models & Impact
    predictions: list[Prediction]
    analog_stats: dict[str, Any]
    priority: PriorityAssessment | None
    resilience: ResilienceEstimate | None

    # Response & Recovery Strategies
    procedures: list[Any]
    episodes: list[Any]
    recommendations: list[Recommendation]
    recovery_analysis: dict[str, Any]

    # Synthesis & Verification
    claims: list[Claim]
    narrative_summary: str
    knowledge_gaps: list[str]
    limitations: list[str]
    llm_usage: dict[str, int]
    revision: int
    fix_list: list[str]
    judge_scores: dict[str, Any]

    # Control & Status
    status: Literal["ok", "degraded", "rejected"]
    error: dict[str, Any] | None
    timings: dict[str, float]
    events: list[dict[str, Any]]
    final_report: Report | None
