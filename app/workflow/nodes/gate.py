"""Gate node performing upfront guardrail inspection and PII redaction."""

from typing import Any

from app.core.guardrails import (
    check_off_topic,
    check_prompt_injection,
    map_or_validate_category,
    redact_pii,
    sanitize_text,
)
from app.workflow.state import WorkflowState


async def gate_node(state: WorkflowState) -> WorkflowState:
    """Validate request, detect injection, redact PII, and check taxonomy."""
    req = state.get("request")
    events = list(state.get("events", []))
    events.append({"node": "gate", "stage": "start"})

    free_text = sanitize_text((req.free_text if req else state.get("free_text", "")) or "")

    if free_text:
        if check_prompt_injection(free_text):
            events.append({"node": "gate", "stage": "rejected", "reason": "prompt_injection"})
            return {
                **state,
                "status": "rejected",
                "error": {
                    "code": "INJECTION_SUSPECTED",
                    "message": "Prompt injection detected in input text.",
                },
                "events": events,
            }

        if check_off_topic(free_text):
            events.append({"node": "gate", "stage": "rejected", "reason": "off_topic"})
            return {
                **state,
                "status": "rejected",
                "error": {
                    "code": "OFF_TOPIC",
                    "message": "Input incident description appears off-topic.",
                },
                "events": events,
            }

        free_text = redact_pii(free_text)

    # Process and validate profile
    raw_profile: dict[str, Any] = state.get("profile", {})
    if req and req.profile:
        raw_profile.update(req.profile.model_dump(exclude_none=True))

    profile: dict[str, Any] = {}
    gaps = list(state.get("knowledge_gaps", []))

    for col, val in raw_profile.items():
        if isinstance(val, str) and col in (
            "disruption_type",
            "industry",
            "supplier_tier",
            "supplier_region",
            "supplier_size",
            "disruption_severity",
        ):
            canon_val, is_valid, is_novel = map_or_validate_category(col, val)
            if not is_valid:
                events.append({"node": "gate", "stage": "rejected", "reason": "invalid_category"})
                return {
                    **state,
                    "status": "rejected",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Invalid categorical value '{val}' for field '{col}'.",
                    },
                    "events": events,
                }
            if is_novel:
                gaps.append(f"Novel category observed for {col}: {val}")
            profile[col] = canon_val or val
        else:
            profile[col] = val

    events.append({"node": "gate", "stage": "completed"})
    return {
        **state,
        "free_text": free_text,
        "profile": profile,
        "knowledge_gaps": gaps,
        "events": events,
    }
