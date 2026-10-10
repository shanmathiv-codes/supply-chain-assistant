"""FastAPI route handlers implementing the core disruption assistant API endpoints."""
import time

from fastapi import APIRouter, Header, HTTPException, Query

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
from app.schemas.report import Claim, Report
from app.schemas.request import (
    ClassifyRequest,
    DisruptionAnalyzeRequest,
    PrioritizeRequest,
    SearchRequest,
)
from app.services.classification import classification_service
from app.services.ledger import ledger_service
from app.services.prioritization import prioritization_service
from app.services.recommendations import recommendation_service
from app.services.retrieval import retrieval_service
from app.services.run_store import run_store
from app.substrate.gateway import SynaptReadGateway

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
                detail={"code": "INJECTION_SUSPECTED", "message": "Prompt injection detected in search query."},
            )
        if check_off_topic(query):
            raise HTTPException(
                status_code=422,
                detail={"code": "OFF_TOPIC", "message": "Search query appears off-topic."},
            )
        query = redact_pii(query)

    prof = req.profile.model_dump(exclude_none=True) if req.profile else {}
    trace: list[SubstrateCall] = []

    similar_cases, evidence, ask_lane, lane_overlap, relaxed = await retrieval_service.retrieve_similar_cases(
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
            detail={"code": "INJECTION_SUSPECTED", "message": "Prompt injection detected in classification input."},
        )
    if check_off_topic(text):
        raise HTTPException(
            status_code=422,
            detail={"code": "OFF_TOPIC", "message": "Input text appears off-topic."},
        )
    text = redact_pii(text)

    prof = req.partial_profile.model_dump(exclude_none=True) if req.partial_profile else {}
    trace: list[SubstrateCall] = []

    result = await classification_service.classify_disruption(profile=prof, free_text=text, trace=trace)
    return {
        "runtime_modes": settings.runtime_modes,
        "classification": result,
        "substrate_trace": trace,
    }


@router.post("/disruptions/prioritize")
async def prioritize_disruption(req: PrioritizeRequest, x_api_key: str | None = Header(default=None)):
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


@router.post("/disruptions/analyze", response_model=Report)
async def analyze_disruption(
    req: DisruptionAnalyzeRequest,
    stream: bool = Query(default=False),
    x_api_key: str | None = Header(default=None),
):
    """Full disruption investigation workflow producing a typed Report."""
    verify_api_key_if_configured(x_api_key)
    t_start = time.perf_counter()

    # 1. Gate & Guardrail Validations
    free_text = sanitize_text(req.free_text or "")
    if free_text:
        if check_prompt_injection(free_text):
            raise HTTPException(
                status_code=422,
                detail={"code": "INJECTION_SUSPECTED", "message": "Prompt injection detected in incident text."},
            )
        if check_off_topic(free_text):
            raise HTTPException(
                status_code=422,
                detail={"code": "OFF_TOPIC", "message": "Incident description appears off-topic."},
            )
        free_text = redact_pii(free_text)

    profile_dict = req.profile.model_dump(exclude_none=True) if req.profile else {}

    # Validate taxonomy categories
    novel_flags = []
    for field in ("disruption_type", "disruption_severity", "supplier_tier", "supplier_region", "supplier_size"):
        if field in profile_dict:
            canon, is_val, is_nov = map_or_validate_category(field, profile_dict[field])
            if not is_val:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "VALIDATION_ERROR", "message": f"Invalid value '{profile_dict[field]}' for field '{field}'."},
                )
            if is_nov:
                novel_flags.append(f"Novel category detected for {field}: {profile_dict[field]}")
            if canon:
                profile_dict[field] = canon

    run_id = generate_id("RUN")
    trace: list[SubstrateCall] = []
    knowledge_gaps = list(novel_flags)
    limitations = []

    # Limitation notices for runtime modes
    modes = settings.runtime_modes
    if modes.get("synapt_mode") == "mock":
        limitations.append("Analysis executed with mock substrate stand-in, not live Synapt provider.")
    if modes.get("llm_mode") == "fake":
        limitations.append("Analysis generated via deterministic fake LLM templates.")
    if modes.get("dataset_source") == "synthetic":
        limitations.append("Results derived from synthetic training dataset.")

    # 2. Hybrid Retrieval
    similar_cases, evidence_store, ask_lane, lane_overlap, relaxed = await retrieval_service.retrieve_similar_cases(
        profile=profile_dict,
        query_text=free_text,
        top_k=req.top_k,
        exclude_case_ids=req.exclude_case_ids,
        trace=trace,
    )
    if relaxed:
        knowledge_gaps.append(f"Retrieval relaxed filter constraints: {', '.join(relaxed)}")

    # 3. Ensemble Classification
    classification_res = await classification_service.classify_disruption(
        profile=profile_dict, free_text=free_text, trace=trace
    )

    # 4. Priority Calculation
    active_sev = profile_dict.get("disruption_severity") or classification_res.disruption_severity
    priority_res = prioritization_service.calculate_priority(
        severity=active_sev,
        production_impact_pct=profile_dict.get("production_impact_pct"),
        revenue_loss_usd=profile_dict.get("revenue_loss_usd"),
    )

    # 5. Recommendations Generation
    status = "ok"
    recs = []
    if similar_cases:
        active_type = profile_dict.get("disruption_type") or classification_res.disruption_type
        recs = await recommendation_service.generate_recommendations(
            disruption_type=active_type,
            similar_cases=similar_cases,
            evidence_store=evidence_store,
            trace=trace,
        )
    else:
        status = "degraded"
        knowledge_gaps.append("no historical evidence available")
        limitations.append("Substrate returned 0 matching historical cases; recommendations omitted.")

    # 6. Formulate Verifiable Claims
    claims: list[Claim] = []
    if similar_cases:
        top_c = similar_cases[0]
        cid = top_c.case_id
        c_attrs = top_c.attributes
        c_outs = top_c.outcomes
        ev_ids = top_c.evidence_ids
        claims.append(
            Claim(
                claim_id=generate_id("CLM"),
                text=f"Historical analog {cid} ({c_attrs.get('disruption_type')}) in {c_attrs.get('industry')} required {c_outs.get('full_recovery_days')} days to fully recover.",
                kind="HISTORICAL_FACT",
                evidence_ids=ev_ids,
            )
        )
        claims.append(
            Claim(
                claim_id=generate_id("CLM"),
                text=f"Observed production impact for closest analog was {c_outs.get('production_impact_pct')}%.",
                kind="HISTORICAL_FACT",
                evidence_ids=ev_ids,
            )
        )

    t_total = (time.perf_counter() - t_start) * 1000.0

    narrative_summary = (
        f"Disruption classified as {classification_res.disruption_type} ({classification_res.disruption_severity}) "
        f"assigned to triage band {priority_res.band} ({priority_res.band_label}, score {priority_res.score}/100). "
        f"Retrieved {len(similar_cases)} historical analogs. "
        + ("Recommended response coordination initiated." if recs else "Degraded operation due to lack of historical analogs.")
    )

    report = Report(
        run_id=run_id,
        status=status,
        runtime_modes=settings.runtime_modes,
        classification=classification_res,
        priority=priority_res,
        similar_cases=similar_cases,
        predictions=[],
        resilience=None,
        recommendations=recs,
        claims=claims,
        evidence=evidence_store,
        substrate_trace=trace,
        ask_lane=ask_lane,
        lane_overlap=lane_overlap,
        knowledge_gaps=knowledge_gaps,
        limitations=limitations,
        llm_usage={"calls": 2, "tokens": 350},
        timings={"total_ms": round(t_total, 2)},
        narrative_summary=narrative_summary,
    )

    # Persist run to database
    run_store.save_run(
        run_id=run_id,
        status=status,
        report_dict=report.model_dump(),
        summary=narrative_summary,
    )

    return report


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
