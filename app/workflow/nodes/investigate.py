"""Investigate node orchestrating hybrid retrieval across Synapt signals and relaxation."""

from app.schemas.evidence import Evidence, SubstrateCall
from app.services.retrieval import retrieval_service
from app.workflow.state import WorkflowState


async def investigate_node(state: WorkflowState) -> WorkflowState:
    """Retrieve historical case analogs using 4 Synapt signals, RRF fusion, and relaxation."""
    events = list(state.get("events", []))
    events.append({"node": "investigate", "stage": "start"})

    profile = state.get("profile", {})
    text = state.get("free_text", "")
    req = state.get("request")
    top_k = req.top_k if req else 5
    exclude_ids = req.exclude_case_ids if req else []

    trace: list[SubstrateCall] = list(state.get("substrate_trace", []))
    gaps = list(state.get("knowledge_gaps", []))

    (
        similar_cases,
        evidence_store,
        ask_lane,
        lane_overlap,
        relaxed,
    ) = await retrieval_service.retrieve_similar_cases(
        profile=profile,
        query_text=text,
        top_k=top_k,
        exclude_case_ids=exclude_ids,
        trace=trace,
    )

    if relaxed:
        gaps.append(f"Retrieval relaxed constraint fields: {', '.join(relaxed)}")

    status = state.get("status", "ok")
    if not similar_cases:
        status = "degraded"
        gaps.append("no historical evidence available")

    # Merge evidence
    merged_ev: dict[str, Evidence] = dict(state.get("evidence", {}))
    merged_ev.update(evidence_store)

    events.append({"node": "investigate", "stage": "completed", "analog_count": len(similar_cases)})
    return {
        **state,
        "similar_cases": similar_cases,
        "evidence": merged_ev,
        "ask_lane": ask_lane,
        "lane_overlap": lane_overlap,
        "relaxed_filters": relaxed,
        "substrate_trace": trace,
        "knowledge_gaps": gaps,
        "status": status,
        "events": events,
    }
