"""Recovery node evaluating historical restoration trajectories and recurring risks."""

from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.workflow.state import WorkflowState


async def recovery_node(state: WorkflowState) -> WorkflowState:
    """Analyze historical recovery timelines, backup supplier impact, and risks."""
    events = list(state.get("events", []))
    events.append({"node": "recovery", "stage": "start"})

    similar_cases = state.get("similar_cases", [])
    if not similar_cases:
        events.append({"node": "recovery", "stage": "skipped", "reason": "no_evidence"})
        return {**state, "recovery_analysis": {}, "events": events}

    profile = state.get("profile", {})
    context = {
        "disruption_type": profile.get("disruption_type"),
        "analog_cases_count": len(similar_cases),
        "has_backup_supplier": profile.get("has_backup_supplier", False),
    }

    try:
        rec_data, _ = await router.complete_structured(
            prompt_name="recovery",
            role="reason",
            messages=[
                {
                    "role": "system",
                    "content": "Analyze historical restoration trajectories and uncertainty.",
                },
                {"role": "user", "content": f"Context: {context}"},
            ],
            context=context,
        )
    except Exception as exc:
        logger.warning(f"Recovery LLM call failed: {exc}")
        rec_data = fake_llm.invoke("recovery", context)

    events.append({"node": "recovery", "stage": "completed"})
    return {
        **state,
        "recovery_analysis": rec_data,
        "events": events,
    }
