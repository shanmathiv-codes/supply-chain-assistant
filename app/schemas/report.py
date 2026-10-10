"""Typed Report, Claim, Prediction, and Assessment schemas."""
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.evidence import Evidence, SubstrateCall

ClaimKind = Literal[
    "HISTORICAL_FACT",
    "DATASET_STATISTIC",
    "MODEL_ESTIMATE",
    "RECOMMENDATION",
    "ASSUMPTION",
]


class Claim(BaseModel):
    """Verifiable typed claim embedded within analysis narrative."""

    claim_id: str
    text: str
    kind: ClaimKind
    evidence_ids: list[str] = Field(default_factory=list)
    model_run_id: str | None = None
    interval: tuple[float, float] | None = None
    ledger_query_id: str | None = None
    population: str | None = None
    n: int | None = None


class CaseSignals(BaseModel):
    cypher_overlap: float | None = None
    node_search: float | None = None
    chunk_search: float | None = None
    exact_lookup: float | None = None


class SimilarCase(BaseModel):
    """Historical disruption case analog retrieved and ranked by substrate."""

    case_id: str
    rank: int
    fused_score: float
    signals: CaseSignals = Field(default_factory=CaseSignals)
    why: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    outcomes: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class AnalogStats(BaseModel):
    n: int
    median: float
    p10: float
    p90: float
    case_ids: list[str] = Field(default_factory=list)
    full_ledger_median: float | None = None
    divergence_warning: str | None = None


class Prediction(BaseModel):
    """Quantitative outcome estimate with conformal prediction interval."""

    target: str
    point: float
    low: float
    high: float
    nominal_coverage: float = 0.80
    model_version: str
    feature_set: str
    top_factors: list[str] = Field(default_factory=list)
    analog: AnalogStats | None = None
    divergence: bool = False


class PriorityAssessment(BaseModel):
    """Priority scoring, triage band assignment, and sensitivity."""

    score: float
    band: str
    band_label: str
    components: dict[str, float]
    reason: str
    sensitivity: dict[str, float] = Field(default_factory=dict)
    based_on_predicted_values: bool = False


class ResilienceEstimate(BaseModel):
    """Resilience index and conditional severity risk."""

    conditional_severity_risk: float = Field(..., ge=0.0, le=1.0)
    resilience_index: float = Field(..., ge=0.0, le=100.0)
    backup_supplier_benefit: str | None = None
    explanation: str


class Recommendation(BaseModel):
    """Actionable mitigation recommendation tied to evidence."""

    title: str
    action: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_type: Literal["procedure", "historical_case", "aggregate_outcome", "assumed"]
    expected_full_recovery_days: float | None = None
    historical_cases_count: int | None = None
    caveats: str | None = None


class ClassificationResult(BaseModel):
    """Ensemble disruption classification output."""

    disruption_type: str
    disruption_severity: str
    confidence: float
    signal_votes: dict[str, dict[str, str]] = Field(default_factory=dict)
    abstained: bool = False
    reason: str


class AskLaneResult(BaseModel):
    answer: str | None = None
    confidence: float | None = None
    query_ref: str | None = None
    cited_case_ids: list[str] = Field(default_factory=list)


class Report(BaseModel):
    """Comprehensive final disruption investigation report."""

    run_id: str
    status: Literal["ok", "degraded", "rejected"]
    runtime_modes: dict[str, str]
    classification: ClassificationResult | None = None
    priority: PriorityAssessment | None = None
    similar_cases: list[SimilarCase] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    resilience: ResilienceEstimate | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    substrate_trace: list[SubstrateCall] = Field(default_factory=list)
    ask_lane: AskLaneResult | None = None
    lane_overlap: float | None = None
    knowledge_gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    llm_usage: dict[str, int] = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)
    narrative_summary: str | None = None
