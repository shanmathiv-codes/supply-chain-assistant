"""Impact node calculating quantitative ML predictions, priority triage, and resilience."""

from app.schemas.request import DisruptionProfile
from app.services.ledger import ledger_service
from app.services.prioritization import prioritization_service
from app.workflow.state import WorkflowState
from ml.registry import model_registry


async def impact_node(state: WorkflowState) -> WorkflowState:
    """Execute ML outcome regressors, priority scoring, resilience, and analog stats."""
    events = list(state.get("events", []))
    events.append({"node": "impact", "stage": "start"})

    profile = dict(state.get("profile", {}))
    classification = state.get("classification")
    similar_cases = state.get("similar_cases", [])
    case_ids = [c.case_id for c in similar_cases]
    gaps = list(state.get("knowledge_gaps", []))

    # Priority calculation
    active_sev = profile.get("disruption_severity") or (
        classification.disruption_severity if classification else "Medium"
    )
    priority_res = prioritization_service.calculate_priority(
        severity=active_sev,
        production_impact_pct=profile.get("production_impact_pct"),
        revenue_loss_usd=profile.get("revenue_loss_usd"),
    )

    # ML Predictions & Resilience
    prof_obj = DisruptionProfile(**profile)
    predictions, resilience, ml_gaps = model_registry.predict_all(
        profile=prof_obj,
        similar_case_ids=case_ids,
    )
    gaps.extend(ml_gaps)

    # Analog Statistics
    analog_stats = ledger_service.compute_analog_stats(case_ids)

    events.append({"node": "impact", "stage": "completed"})
    return {
        **state,
        "priority": priority_res,
        "predictions": predictions,
        "resilience": resilience,
        "analog_stats": analog_stats,
        "knowledge_gaps": gaps,
        "events": events,
    }
