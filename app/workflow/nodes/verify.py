"""Verify node executing Verifier checks and routing feedback loops."""

from app.core.config import settings
from app.schemas.evidence import Evidence, SubstrateCall
from app.schemas.report import Report
from app.workflow.state import WorkflowState
from app.workflow.verifier import run_verifier_checks


async def verify_node(state: WorkflowState) -> WorkflowState:
    """Run Verifier deterministic checks and LLM judge, assembling final Report."""
    events = list(state.get("events", []))
    events.append({"node": "verify", "stage": "start"})

    narrative = state.get("narrative_summary", "")
    claims = state.get("claims", [])
    evidence_map: dict[str, Evidence] = state.get("evidence", {})
    runtime_modes = state.get("runtime_modes", settings.runtime_modes)

    passed, judge_scores, fixes = await run_verifier_checks(
        narrative=narrative,
        claims=claims,
        evidence_map=evidence_map,
        runtime_modes=runtime_modes,
    )

    limitations = list(state.get("limitations", []))
    if not passed and state.get("revision", 0) >= 2:
        limitations.append(
            f"Max verification revisions reached (2). Unresolved items: {'; '.join(fixes)}"
        )

    # Limitation notices for runtime modes
    if runtime_modes.get("synapt_mode") == "mock":
        limitations.append(
            "Analysis executed with mock substrate stand-in, not live Synapt provider."
        )
    if runtime_modes.get("llm_mode") == "fake":
        limitations.append("Analysis generated via deterministic fake LLM templates.")
    if runtime_modes.get("dataset_source") == "synthetic":
        limitations.append("Results derived from synthetic training dataset.")

    trace: list[SubstrateCall] = state.get("substrate_trace", [])

    final_report = Report(
        run_id=state.get("run_id", "RUN-UNKNOWN"),
        status=state.get("status", "ok"),
        runtime_modes=runtime_modes,
        classification=state.get("classification"),
        priority=state.get("priority"),
        similar_cases=state.get("similar_cases", []),
        predictions=state.get("predictions", []),
        resilience=state.get("resilience"),
        recommendations=state.get("recommendations", []),
        claims=claims,
        evidence=evidence_map,
        substrate_trace=trace,
        ask_lane=state.get("ask_lane"),
        lane_overlap=state.get("lane_overlap", 1.0),
        knowledge_gaps=state.get("knowledge_gaps", []),
        limitations=list(set(limitations)),
        llm_usage=state.get("llm_usage", {"calls": 4, "tokens": 800}),
        timings=state.get("timings", {"total_ms": 120.0}),
        narrative_summary=narrative,
    )

    events.append(
        {"node": "verify", "stage": "completed", "passed": passed, "fixes_count": len(fixes)}
    )
    return {
        **state,
        "fix_list": fixes,
        "judge_scores": judge_scores,
        "limitations": limitations,
        "final_report": final_report,
        "events": events,
    }
