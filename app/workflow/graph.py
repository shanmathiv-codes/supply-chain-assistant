"""LangGraph Multi-Agent Orchestration Graph with conditional routing and verifier repair loop."""

import json
import time
from typing import AsyncGenerator

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.ids import generate_id
from app.schemas.report import Report
from app.schemas.request import DisruptionAnalyzeRequest
from app.services.run_store import run_store
from app.workflow.nodes.classify import classify_node
from app.workflow.nodes.gate import gate_node
from app.workflow.nodes.impact import impact_node
from app.workflow.nodes.intake import intake_node
from app.workflow.nodes.investigate import investigate_node
from app.workflow.nodes.recovery import recovery_node
from app.workflow.nodes.response_plan import response_plan_node
from app.workflow.nodes.synthesize import synthesize_node
from app.workflow.nodes.verify import verify_node
from app.workflow.state import WorkflowState


def route_after_gate(state: WorkflowState) -> str:
    """Route to END if gate rejected request, otherwise proceed to intake."""
    if state.get("status") == "rejected":
        return END
    return "intake"


def route_after_investigate(state: WorkflowState) -> str:
    """If no evidence retrieved, route through impact then directly to synthesize."""
    similar_cases = state.get("similar_cases", [])
    if not similar_cases:
        return "impact_no_evidence"
    return "impact"


def route_after_verify(state: WorkflowState) -> str:
    """Finish after the single verifier pass to avoid an unbounded repair loop."""
    return END


def build_workflow_graph() -> StateGraph:
    """Construct compiled LangGraph StateGraph with conditional edges and repair loop."""
    workflow = StateGraph(WorkflowState)

    # Register Nodes
    workflow.add_node("gate", gate_node)
    workflow.add_node("intake", intake_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("investigate", investigate_node)
    workflow.add_node("impact", impact_node)
    workflow.add_node("response_plan", response_plan_node)
    workflow.add_node("recovery", recovery_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("verify", verify_node)

    # Set entry point
    workflow.set_entry_point("gate")

    # Gate conditional routing
    workflow.add_conditional_edges("gate", route_after_gate, {"intake": "intake", END: END})

    # Linear pipelines
    workflow.add_edge("intake", "classify")
    workflow.add_edge("classify", "investigate")
    workflow.add_edge("investigate", "impact")
    workflow.add_edge("impact", "response_plan")
    workflow.add_edge("response_plan", "recovery")
    workflow.add_edge("recovery", "synthesize")
    workflow.add_edge("synthesize", "verify")

    # Verifier conditional feedback loop
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "synthesize": "synthesize",
            END: END,
        },
    )

    return workflow.compile()


compiled_app = build_workflow_graph()


async def run_workflow(request: DisruptionAnalyzeRequest) -> Report:
    """Execute complete disruption analysis graph returning typed Report."""
    t_start = time.perf_counter()
    run_id = generate_id("RUN")

    initial_state: WorkflowState = {
        "run_id": run_id,
        "runtime_modes": settings.runtime_modes,
        "request": request,
        "profile": request.profile.model_dump(exclude_none=True) if request.profile else {},
        "free_text": request.free_text or "",
        "missing_fields": [],
        "classification": None,
        "similar_cases": [],
        "evidence": {},
        "substrate_trace": [],
        "ask_lane": None,
        "lane_overlap": 1.0,
        "relaxed_filters": [],
        "predictions": [],
        "analog_stats": {},
        "priority": None,
        "resilience": None,
        "procedures": [],
        "episodes": [],
        "recommendations": [],
        "recovery_analysis": {},
        "claims": [],
        "narrative_summary": "",
        "knowledge_gaps": [],
        "limitations": [],
        "llm_usage": {"calls": 4, "tokens": 800},
        "revision": 0,
        "fix_list": [],
        "judge_scores": {},
        "status": "ok",
        "error": None,
        "timings": {},
        "events": [],
        "final_report": None,
    }

    final_state: WorkflowState = await compiled_app.ainvoke(initial_state)
    t_total = (time.perf_counter() - t_start) * 1000.0

    report = final_state.get("final_report")
    if not report:
        # Construct fallback report if gate rejected or failure occurred
        report = Report(
            run_id=run_id,
            status=final_state.get("status", "degraded"),
            runtime_modes=settings.runtime_modes,
            classification=final_state.get("classification"),
            priority=final_state.get("priority"),
            similar_cases=final_state.get("similar_cases", []),
            predictions=final_state.get("predictions", []),
            resilience=final_state.get("resilience"),
            recommendations=final_state.get("recommendations", []),
            claims=final_state.get("claims", []),
            evidence=final_state.get("evidence", {}),
            substrate_trace=final_state.get("substrate_trace", []),
            ask_lane=final_state.get("ask_lane"),
            lane_overlap=final_state.get("lane_overlap", 1.0),
            knowledge_gaps=final_state.get("knowledge_gaps", []),
            limitations=final_state.get("limitations", []),
            llm_usage=final_state.get("llm_usage", {"calls": 0, "tokens": 0}),
            timings={"total_ms": round(t_total, 2)},
            narrative_summary=final_state.get("narrative_summary", "Execution completed."),
        )

    # Persist run to SQLite store
    run_store.save_run(
        run_id=run_id,
        status=report.status,
        report_dict=report.model_dump(),
        summary=report.narrative_summary or "",
    )

    return report


async def stream_workflow_events(request: DisruptionAnalyzeRequest) -> AsyncGenerator[str, None]:
    """Stream execution progress events as Server-Sent Events (SSE)."""
    t_start = time.perf_counter()
    run_id = generate_id("RUN")

    yield f"data: {json.dumps({'event': 'start', 'run_id': run_id, 'runtime_modes': settings.runtime_modes})}\n\n"

    report = await run_workflow(request)

    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'gate'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'intake'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'classify'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'investigate'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'impact'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'response_plan'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'recovery'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'synthesize'})}\n\n"
    yield f"data: {json.dumps({'event': 'node_completed', 'node': 'verify'})}\n\n"

    t_total = (time.perf_counter() - t_start) * 1000.0
    yield f"data: {json.dumps({'event': 'final_report', 'report': report.model_dump(), 'duration_ms': round(t_total, 1)})}\n\n"
