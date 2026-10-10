"""Classification node executing ensemble voting for disruption type and severity."""

from app.schemas.evidence import SubstrateCall
from app.services.classification import classification_service
from app.workflow.state import WorkflowState


async def classify_node(state: WorkflowState) -> WorkflowState:
    """Classify incident type and severity using ensemble signals."""
    events = list(state.get("events", []))
    events.append({"node": "classify", "stage": "start"})

    profile = state.get("profile", {})
    text = state.get("free_text", "")
    trace: list[SubstrateCall] = list(state.get("substrate_trace", []))

    cls_result = await classification_service.classify_disruption(
        profile=profile,
        free_text=text,
        trace=trace,
    )

    events.append({"node": "classify", "stage": "completed"})
    return {
        **state,
        "classification": cls_result,
        "substrate_trace": trace,
        "events": events,
    }
