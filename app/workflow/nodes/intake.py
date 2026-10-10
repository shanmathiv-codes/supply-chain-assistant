"""Intake node parsing free text into structured profile using fast LLM and taxonomy."""

from typing import Any

from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.workflow.state import WorkflowState


async def intake_node(state: WorkflowState) -> WorkflowState:
    """Extract missing attributes from narrative text and populate profile."""
    events = list(state.get("events", []))
    events.append({"node": "intake", "stage": "start"})

    text = state.get("free_text", "")
    profile: dict[str, Any] = dict(state.get("profile", {}))
    missing_fields = list(state.get("missing_fields", []))

    if text:
        try:
            res_dict, _ = await router.complete_structured(
                prompt_name="intake",
                role="fast",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract structured disruption profile from narrative.",
                    },
                    {"role": "user", "content": text},
                ],
                context={"text": text},
            )
        except Exception as exc:
            logger.warning(f"Intake LLM call failed: {exc}")
            res_dict = fake_llm.invoke("intake", {"text": text})

        for k, v in res_dict.items():
            if k in (
                "disruption_type",
                "industry",
                "supplier_tier",
                "supplier_region",
                "supplier_size",
                "disruption_severity",
                "has_backup_supplier",
            ):
                if v is not None and k not in profile:
                    profile[k] = v
        missing_fields = res_dict.get("missing_fields", [])

    events.append({"node": "intake", "stage": "completed"})
    return {
        **state,
        "profile": profile,
        "missing_fields": missing_fields,
        "events": events,
    }
