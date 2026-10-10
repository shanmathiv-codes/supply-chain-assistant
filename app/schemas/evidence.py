"""Typed Evidence and Substrate Call schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

ProvenanceMode = Literal["MCP", "REPLAY", "MOCK"]


class Evidence(BaseModel):
    """Atomic verifiable unit of knowledge retrieved from the substrate."""

    evidence_id: str = Field(..., description="Unique evidence identifier (e.g. EV-...)")
    tool: str = Field(..., description="Synapt tool that returned this evidence")
    provider_id: str = Field(..., description="Synapt provider ID")
    provenance_mode: ProvenanceMode = Field(..., description="MCP, REPLAY, or MOCK")
    node_id: str | None = Field(default=None, description="Graph node identifier")
    doc_id: str | None = Field(default=None, description="Source document identifier")
    chunk_id: str | None = Field(default=None, description="Text chunk identifier")
    case_id: str | None = Field(
        default=None, description="Disruption ID associated with this evidence"
    )
    text_span: str | None = Field(default=None, description="Raw text quote or passage snippet")
    score: float | None = Field(default=None, description="Similarity or relevance score")
    query_ref: str | None = Field(
        default=None, description="Query reference token for feedback tracking"
    )
    template: str | None = Field(default=None, description="Cypher template name if applicable")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured properties"
    )


class SubstrateCall(BaseModel):
    """Audit log entry for an interaction with the substrate gateway."""

    tool: str
    params_hash: str
    template: str | None = None
    latency_ms: float
    rows: int
    ok: bool
    error: str | None = None
    query_ref: str | None = None
    correlation_id: str | None = None
