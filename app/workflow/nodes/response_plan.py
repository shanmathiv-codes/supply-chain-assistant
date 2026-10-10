"""Response plan node generating grounded tactical mitigation actions."""

from app.schemas.evidence import Evidence, SubstrateCall
from app.schemas.report import Recommendation
from app.services.recommendations import recommendation_service
from app.workflow.state import WorkflowState


async def response_plan_node(state: WorkflowState) -> WorkflowState:
    """Generate mitigation recommendations grounded in SOPs and response outcomes."""
    events = list(state.get("events", []))
    events.append({"node": "response_plan", "stage": "start"})

    similar_cases = state.get("similar_cases", [])
    if not similar_cases:
        events.append({"node": "response_plan", "stage": "skipped", "reason": "no_evidence"})
        return {**state, "recommendations": [], "events": events}

    profile = state.get("profile", {})
    classification = state.get("classification")
    disruption_type = profile.get("disruption_type") or (
        classification.disruption_type if classification else "Operational Failure"
    )

    evidence_store: dict[str, Evidence] = dict(state.get("evidence", {}))
    trace: list[SubstrateCall] = list(state.get("substrate_trace", []))

    recs: list[Recommendation] = await recommendation_service.generate_recommendations(
        disruption_type=disruption_type,
        similar_cases=similar_cases,
        evidence_store=evidence_store,
        trace=trace,
    )

    events.append({"node": "response_plan", "stage": "completed", "count": len(recs)})
    return {
        **state,
        "recommendations": recs,
        "evidence": evidence_store,
        "substrate_trace": trace,
        "events": events,
    }
