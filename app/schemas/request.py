"""API and workflow input request models."""

from pydantic import BaseModel, Field


class DisruptionProfile(BaseModel):
    """Structured disruption attributes adhering to dataset taxonomy."""

    disruption_id: str | None = Field(
        default=None, description="Optional ID if querying existing case"
    )
    disruption_type: str | None = Field(default=None, description="Type of disruption event")
    industry: str | None = Field(default=None, description="Target industry vertical")
    supplier_tier: str | None = Field(default=None, description="Supplier tier level")
    supplier_region: str | None = Field(default=None, description="Supplier geography")
    supplier_size: str | None = Field(default=None, description="Supplier organization size")
    has_backup_supplier: bool | None = Field(
        default=None, description="Whether backup supplier exists"
    )
    disruption_severity: str | None = Field(default=None, description="Severity rating")
    production_impact_pct: float | None = Field(
        default=None, ge=0.0, le=100.0, description="Observed or estimated production loss %"
    )
    revenue_loss_usd: float | None = Field(
        default=None, ge=0.0, description="Observed direct revenue loss in USD"
    )
    response_type: str | None = Field(
        default=None, description="Response mitigation strategy if chosen"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "disruption_type": "Labor Strike",
                "industry": "Automotive",
                "supplier_tier": "Tier 1",
                "supplier_region": "North America",
                "supplier_size": "Medium",
                "has_backup_supplier": False,
                "disruption_severity": "High",
            }
        }
    }


class DisruptionAnalyzeRequest(BaseModel):
    """Request payload for full disruption investigation workflow."""

    profile: DisruptionProfile | None = Field(default=None, description="Structured attributes")
    free_text: str | None = Field(
        default=None, max_length=2000, description="Unstructured incident description"
    )
    exclude_case_ids: list[str] = Field(
        default_factory=list, description="Case IDs to omit from retrieval"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum similar cases to return")


class SearchRequest(BaseModel):
    """Request payload for hybrid disruption case retrieval."""

    profile: DisruptionProfile | None = None
    query_text: str | None = Field(default=None, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    strict_filter: bool = Field(default=False)
    exclude_case_ids: list[str] = Field(default_factory=list)


class ClassifyRequest(BaseModel):
    """Request payload for disruption classification."""

    free_text: str = Field(..., min_length=3, max_length=2000)
    partial_profile: DisruptionProfile | None = None


class PrioritizeRequest(BaseModel):
    """Request payload for disruption prioritization scoring."""

    severity: str = Field(..., description="Low, Medium, High, or Critical")
    production_impact_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    revenue_loss_usd: float | None = Field(default=None, ge=0.0)
    weights: dict[str, float] | None = None


class PredictRequest(BaseModel):
    """Request payload for ML outcome predictions and resilience estimates."""

    profile: DisruptionProfile
    target: str | None = None
