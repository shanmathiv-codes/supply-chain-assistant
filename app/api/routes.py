"""FastAPI route handlers implementing the core disruption assistant API endpoints."""

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.guardrails import (
    check_off_topic,
    check_prompt_injection,
    map_or_validate_category,
    redact_pii,
    sanitize_text,
)
from app.core.ids import generate_id
from app.schemas.evidence import SubstrateCall
from app.schemas.feedback import FeedbackSubmission
from app.schemas.request import (
    ClassifyRequest,
    DisruptionAnalyzeRequest,
    PredictRequest,
    PrioritizeRequest,
    SearchRequest,
)
from app.services.classification import classification_service
from app.services.ledger import ledger_service
from app.services.prioritization import prioritization_service
from app.services.retrieval import retrieval_service
from app.services.run_store import run_store
from app.substrate.gateway import SynaptReadGateway
from app.workflow.graph import run_workflow, stream_workflow_events
from ml.registry import model_registry

router = APIRouter()
gateway = SynaptReadGateway()


def verify_api_key_if_configured(x_api_key: str | None = Header(default=None)):
    if settings.api_key and settings.api_key.strip():
        if not x_api_key or x_api_key.strip() != settings.api_key.strip():
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-API-Key header."},
            )


@router.get("/health")
async def health_check():
    """System health endpoint reporting active modes and substrate connectivity."""
    substrate_health = {"status": "ok"}
    episodes_health = {"status": "ok"}
    try:
        substrate_health = await gateway.health()
    except Exception as exc:
        substrate_health = {"status": "degraded", "error": str(exc)}

    status = "ok" if substrate_health.get("status") == "ok" else "degraded"
    return {
        "status": status,
        "runtime_modes": settings.runtime_modes,
        "substrate": substrate_health,
        "episodes_store": episodes_health,
        "versions": {
            "api_version": "1.0.0",
            "model_version": "v1.0-ridge-rf",
        },
    }


@router.post("/disruptions/search")
async def search_disruptions(req: SearchRequest, x_api_key: str | None = Header(default=None)):
    """Search for historical disruption analogs matching profile and query text."""
    verify_api_key_if_configured(x_api_key)

    query = sanitize_text(req.query_text or "")
    if query:
        if check_prompt_injection(query):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INJECTION_SUSPECTED",
                    "message": "Prompt injection detected in search query.",
                },
            )
        if check_off_topic(query):
            raise HTTPException(
                status_code=422,
                detail={"code": "OFF_TOPIC", "message": "Search query appears off-topic."},
            )
        query = redact_pii(query)

    prof = req.profile.model_dump(exclude_none=True) if req.profile else {}
    trace: list[SubstrateCall] = []

    (
        similar_cases,
        evidence,
        ask_lane,
        lane_overlap,
        relaxed,
    ) = await retrieval_service.retrieve_similar_cases(
        profile=prof,
        query_text=query,
        top_k=req.top_k,
        exclude_case_ids=req.exclude_case_ids,
        trace=trace,
    )

    return {
        "runtime_modes": settings.runtime_modes,
        "similar_cases": similar_cases,
        "evidence": evidence,
        "ask_lane": ask_lane,
        "lane_overlap": lane_overlap,
        "relaxed_filters": relaxed,
        "substrate_trace": trace,
    }


@router.post("/disruptions/classify")
async def classify_disruption(req: ClassifyRequest, x_api_key: str | None = Header(default=None)):
    """Classify incident type and severity using ensemble consensus voting."""
    verify_api_key_if_configured(x_api_key)

    text = sanitize_text(req.free_text)
    if check_prompt_injection(text):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INJECTION_SUSPECTED",
                "message": "Prompt injection detected in classification input.",
            },
        )
    if check_off_topic(text):
        raise HTTPException(
            status_code=422,
            detail={"code": "OFF_TOPIC", "message": "Input text appears off-topic."},
        )
    text = redact_pii(text)

    prof = req.partial_profile.model_dump(exclude_none=True) if req.partial_profile else {}
    trace: list[SubstrateCall] = []

    result = await classification_service.classify_disruption(
        profile=prof, free_text=text, trace=trace
    )
    return {
        "runtime_modes": settings.runtime_modes,
        "classification": result,
        "substrate_trace": trace,
    }


@router.post("/disruptions/prioritize")
async def prioritize_disruption(
    req: PrioritizeRequest, x_api_key: str | None = Header(default=None)
):
    """Calculate formula-grounded priority score (0-100) and triage band (P1-P4)."""
    verify_api_key_if_configured(x_api_key)

    assessment = prioritization_service.calculate_priority(
        severity=req.severity,
        production_impact_pct=req.production_impact_pct,
        revenue_loss_usd=req.revenue_loss_usd,
    )
    return {
        "runtime_modes": settings.runtime_modes,
        "priority": assessment,
    }


@router.post("/disruptions/predict")
async def predict_outcomes(req: PredictRequest, x_api_key: str | None = Header(default=None)):
    """Predict outcome targets with conformal prediction intervals and resilience."""
    verify_api_key_if_configured(x_api_key)
    predictions, resilience, gaps = model_registry.predict_all(req.profile)
    return {
        "runtime_modes": settings.runtime_modes,
        "predictions": predictions,
        "resilience": resilience,
        "knowledge_gaps": gaps,
    }


@router.post("/disruptions/analyze")
async def analyze_disruption(
    req: DisruptionAnalyzeRequest,
    stream: bool = Query(default=False),
    x_api_key: str | None = Header(default=None),
):
    """Full disruption investigation workflow producing a typed Report."""
    verify_api_key_if_configured(x_api_key)

    # Upfront guardrail checks
    free_text = sanitize_text(req.free_text or "")
    if free_text:
        if check_prompt_injection(free_text):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INJECTION_SUSPECTED",
                    "message": "Prompt injection detected in incident text.",
                },
            )
        if check_off_topic(free_text):
            raise HTTPException(
                status_code=422,
                detail={"code": "OFF_TOPIC", "message": "Incident description appears off-topic."},
            )

    if req.profile:
        p_dict = req.profile.model_dump(exclude_none=True)
        for field in (
            "disruption_type",
            "disruption_severity",
            "supplier_tier",
            "supplier_region",
            "supplier_size",
        ):
            if field in p_dict:
                _, is_val, _ = map_or_validate_category(field, p_dict[field])
                if not is_val:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "VALIDATION_ERROR",
                            "message": f"Invalid value '{p_dict[field]}' for field '{field}'.",
                        },
                    )

    if stream:
        return StreamingResponse(
            stream_workflow_events(req),
            media_type="text/event-stream",
        )

    return await run_workflow(req)


@router.get("/cases/{case_id}")
async def get_case_detail(case_id: str, x_api_key: str | None = Header(default=None)):
    """Fetch complete ledger record and Synapt evidence for a specific case."""
    verify_api_key_if_configured(x_api_key)

    case_rec = ledger_service.get_case(case_id)
    if not case_rec:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Case ID '{case_id}' not found in ledger."},
        )

    trace: list[SubstrateCall] = []
    synapt_evs = await gateway.find_exact(label=case_id, trace=trace)

    return {
        "case_id": case_id,
        "ledger_record": case_rec,
        "synapt_evidence": synapt_evs,
        "substrate_trace": trace,
        "runtime_modes": settings.runtime_modes,
    }


@router.get("/runs/{run_id}")
async def get_stored_run(run_id: str, x_api_key: str | None = Header(default=None)):
    """Fetch stored investigation report by run_id."""
    verify_api_key_if_configured(x_api_key)

    run_data = run_store.get_run(run_id)
    if not run_data:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": f"Run ID '{run_id}' not found in store."},
        )
    return run_data


@router.post("/feedback")
async def submit_feedback(fb: FeedbackSubmission, x_api_key: str | None = Header(default=None)):
    """Submit user feedback for an investigation report."""
    verify_api_key_if_configured(x_api_key)

    fb_id = generate_id("FB")
    return {
        "feedback_id": fb_id,
        "status": "pending",
        "message": "Feedback received and queued for review.",
    }
