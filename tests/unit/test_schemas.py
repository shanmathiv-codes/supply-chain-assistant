"""Unit tests for Pydantic domain models and schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.errors import ErrorResponse
from app.schemas.evidence import Evidence
from app.schemas.report import Claim
from app.schemas.request import DisruptionProfile


def test_evidence_model_valid():
    ev = Evidence(
        evidence_id="EV-000001-a1b2c3",
        tool="trident_get_chunks",
        provider_id="prov-1",
        provenance_mode="MOCK",
        case_id="DIS-001",
        text_span="Severe factory fire disrupted Tier 1 semiconductor supplier.",
        score=0.92,
    )
    assert ev.evidence_id.startswith("EV-")
    assert ev.provenance_mode == "MOCK"

def test_disruption_profile_validation():
    # Valid profile
    profile = DisruptionProfile(
        disruption_type="Labor Strike",
        industry="Automotive",
        production_impact_pct=45.5,
        disruption_severity="High",
    )
    assert profile.production_impact_pct == 45.5

    # Out of range production impact % must raise ValidationError
    with pytest.raises(ValidationError):
        DisruptionProfile(production_impact_pct=150.0)

def test_claim_model():
    claim = Claim(
        claim_id="CLM-01",
        text="Historical cases with Tier 1 suppliers experienced median 42 days recovery.",
        kind="HISTORICAL_FACT",
        evidence_ids=["EV-001"],
        n=15,
    )
    assert claim.kind == "HISTORICAL_FACT"
    assert "EV-01" not in claim.evidence_ids
    assert "EV-001" in claim.evidence_ids

def test_error_response_format():
    err = ErrorResponse(
        error={
            "code": "VALIDATION_ERROR",
            "message": "Field out of range",
            "details": {"field": "production_impact_pct"},
        }
    )
    assert err.error.code == "VALIDATION_ERROR"
    assert err.error.message == "Field out of range"
