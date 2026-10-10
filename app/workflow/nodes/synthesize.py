"""Synthesis node assembling typed verifiable claims and narrative summary."""

from app.core.ids import generate_id
from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.schemas.report import Claim
from app.workflow.state import WorkflowState


async def synthesize_node(state: WorkflowState) -> WorkflowState:
    """Synthesize executive narrative and generate typed verifiable claims."""
    revision = state.get("revision", 0)
    events = list(state.get("events", []))
    events.append({"node": "synthesize", "stage": "start", "revision": revision})

    similar_cases = state.get("similar_cases", [])
    predictions = state.get("predictions", [])
    priority = state.get("priority")
    classification = state.get("classification")
    recs = state.get("recommendations", [])
    fix_list = state.get("fix_list", [])

    claims: list[Claim] = []

    # 1. Historical Fact Claims citing analogs
    for case in similar_cases[:2]:
        cid = case.case_id
        c_attrs = case.attributes
        c_outs = case.outcomes
        ev_ids = case.evidence_ids
        claims.append(
            Claim(
                claim_id=generate_id("CLM"),
                text=f"Historical analog {cid} ({c_attrs.get('disruption_type')}) in {c_attrs.get('industry')} required {c_outs.get('full_recovery_days')} days to fully recover.",
                kind="HISTORICAL_FACT",
                evidence_ids=ev_ids,
            )
        )

    # 2. Model Estimate Claims with conformal intervals
    for pred in predictions:
        claims.append(
            Claim(
                claim_id=generate_id("CLM"),
                text=f"Estimated {pred.target} point prediction is {pred.point} [80% conformal interval: {pred.low} - {pred.high}].",
                kind="MODEL_ESTIMATE",
                interval=(pred.low, pred.high),
                model_run_id=pred.model_version,
            )
        )

    # 3. Recommendation Claims
    for r in recs:
        claims.append(
            Claim(
                claim_id=generate_id("CLM"),
                text=f"Mitigation action '{r.title}': {r.action}",
                kind="RECOMMENDATION",
                evidence_ids=r.evidence_ids,
            )
        )

    # 4. Generate Narrative Summary
    context = {
        "classification": classification.model_dump() if classification else {},
        "priority": priority.model_dump() if priority else {},
        "claims_count": len(claims),
        "fix_list": fix_list,
        "evidence_ids": [c.evidence_ids[0] for c in similar_cases if c.evidence_ids],
    }

    try:
        synth_data, _ = await router.complete_structured(
            prompt_name="synthesize",
            role="reason",
            messages=[
                {
                    "role": "system",
                    "content": "Assemble final executive disruption investigation narrative.",
                },
                {"role": "user", "content": f"Context: {context}"},
            ],
            context=context,
        )
        narrative = synth_data.get("narrative_summary")
    except Exception as exc:
        logger.warning(f"Synthesis LLM call failed: {exc}")
        synth_data = fake_llm.invoke("synthesize", context)
        narrative = synth_data.get("narrative_summary")

    if not narrative:
        d_type = classification.disruption_type if classification else "Disruption"
        d_sev = classification.disruption_severity if classification else "Medium"
        p_band = priority.band if priority else "P3"
        narrative = (
            f"Investigation concluded for {d_type} ({d_sev}) event. "
            f"Assigned to triage band {p_band} with {len(similar_cases)} historical analogs retrieved. "
            f"Response actions and predictive outcomes established with historical uncertainty."
        )

    events.append({"node": "synthesize", "stage": "completed", "claims_count": len(claims)})
    return {
        **state,
        "claims": claims,
        "narrative_summary": narrative,
        "events": events,
    }
