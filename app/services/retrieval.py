"""Hybrid retrieval service orchestrating 4 Synapt signals, RRF fusion, relaxation ladder, and lane agreement."""
from typing import Any

from app.core.config import load_yaml_config
from app.core.ids import generate_id
from app.core.logging import logger
from app.schemas.evidence import Evidence, SubstrateCall
from app.schemas.report import AskLaneResult, SimilarCase
from app.services.ledger import ledger_service
from app.substrate.case_resolver import resolve_case_id
from app.substrate.fusion import fuse_signals
from app.substrate.gateway import SynaptReadGateway

SYNAPT_CONFIG = load_yaml_config("synapt.yaml")
RELAXATION_ORDER = SYNAPT_CONFIG.get("relaxation_ladder", {}).get("order", [
    "supplier_size",
    "supplier_region",
    "supplier_tier",
    "industry",
])
MIN_CASES_THRESHOLD = SYNAPT_CONFIG.get("relaxation_ladder", {}).get("min_cases_threshold", 5)


class RetrievalService:
    """Orchestrates 4-signal Synapt retrieval, reciprocal rank fusion, filter relaxation, and lane agreement."""

    def __init__(self, gateway: SynaptReadGateway | None = None):
        self.gateway = gateway or SynaptReadGateway()

    async def retrieve_similar_cases(
        self,
        profile: dict[str, Any],
        query_text: str | None = None,
        top_k: int = 5,
        exclude_case_ids: list[str] | None = None,
        trace: list[SubstrateCall] | None = None,
    ) -> tuple[list[SimilarCase], dict[str, Evidence], AskLaneResult | None, float, list[str]]:
        """Execute hybrid retrieval returning ranked SimilarCase analogs, collected evidence,

        ask lane result, Jaccard lane overlap, and list of relaxed filters (if any).
        """
        exclude_ids = exclude_case_ids or []
        effective_filters = {k: v for k, v in profile.items() if v is not None}
        relaxed_filters_history = []

        # 1. Structured Overlap Signal (Cypher attr_overlap_rank)
        cypher_cases: list[str] = []
        cypher_whys: dict[str, list[str]] = {}
        evidence_store: dict[str, Evidence] = {}

        # First attempt strict or soft Cypher retrieval
        try:
            cypher_res = await self.gateway.cypher(
                template_name="attr_overlap_rank",
                params={
                    "disruption_type": profile.get("disruption_type"),
                    "industry": profile.get("industry"),
                    "supplier_tier": profile.get("supplier_tier"),
                    "supplier_region": profile.get("supplier_region"),
                    "supplier_size": profile.get("supplier_size"),
                    "disruption_severity": profile.get("disruption_severity"),
                    "exclude_case_ids": exclude_ids,
                    "limit": top_k * 3,
                },
                trace=trace,
            )
            for row in cypher_res:
                cid = resolve_case_id(row)
                if cid and cid not in exclude_ids and cid not in cypher_cases:
                    cypher_cases.append(cid)
                    cypher_whys[cid] = row.get("why", ["Matching profile attributes"])
        except Exception as exc:
            logger.warning(f"Cypher retrieval signal failed: {exc}")

        # Relaxation ladder check if Cypher yielded fewer than min threshold
        if len(cypher_cases) < MIN_CASES_THRESHOLD:
            for drop_field in RELAXATION_ORDER:
                if drop_field in effective_filters:
                    effective_filters.pop(drop_field)
                    relaxed_filters_history.append(drop_field)
                    try:
                        relax_res = await self.gateway.cypher(
                            template_name="attr_overlap_rank",
                            params={
                                "disruption_type": effective_filters.get("disruption_type"),
                                "industry": effective_filters.get("industry"),
                                "supplier_tier": effective_filters.get("supplier_tier"),
                                "supplier_region": effective_filters.get("supplier_region"),
                                "supplier_size": effective_filters.get("supplier_size"),
                                "disruption_severity": effective_filters.get("disruption_severity"),
                                "exclude_case_ids": exclude_ids,
                                "limit": top_k * 3,
                            },
                            trace=trace,
                        )
                        for row in relax_res:
                            cid = resolve_case_id(row)
                            if cid and cid not in exclude_ids and cid not in cypher_cases:
                                cypher_cases.append(cid)
                                cypher_whys[cid] = row.get("why", ["Relaxed match"])
                        if len(cypher_cases) >= MIN_CASES_THRESHOLD:
                            break
                    except Exception:
                        pass

        # 2. Graph Semantic Signal (trident_search over nodes)
        node_cases: list[str] = []
        search_query = query_text or f"{profile.get('disruption_type', '')} {profile.get('industry', '')} {profile.get('disruption_severity', '')}".strip()
        if search_query:
            try:
                node_evs = await self.gateway.search_nodes(query=search_query, top_k=top_k * 2, trace=trace)
                for ev in node_evs:
                    cid = resolve_case_id(ev.text_span or ev.case_id or ev.node_id)
                    if cid and cid not in exclude_ids and cid not in node_cases:
                        node_cases.append(cid)
                        evidence_store[ev.evidence_id] = ev
            except Exception as exc:
                logger.warning(f"Node search signal failed: {exc}")

        # 3. Text Semantic Signal (trident_get_chunks over narrative text)
        chunk_cases: list[str] = []
        if search_query:
            try:
                chunk_evs = await self.gateway.get_chunks(query=search_query, top_k=top_k * 2, trace=trace)
                for ev in chunk_evs:
                    cid = resolve_case_id(ev.text_span or ev.case_id)
                    if cid and cid not in exclude_ids and cid not in chunk_cases:
                        chunk_cases.append(cid)
                        evidence_store[ev.evidence_id] = ev
            except Exception as exc:
                logger.warning(f"Chunk search signal failed: {exc}")

        # 4. Exact Signal (trident_find_exact for disruption_type / severity)
        exact_cases: list[str] = []
        exact_label = profile.get("disruption_type") or search_query
        if exact_label:
            try:
                exact_evs = await self.gateway.find_exact(label=str(exact_label), trace=trace)
                for ev in exact_evs:
                    cid = resolve_case_id(ev.text_span or ev.case_id or ev.node_id)
                    if cid and cid not in exclude_ids and cid not in exact_cases:
                        exact_cases.append(cid)
                        evidence_store[ev.evidence_id] = ev
            except Exception as exc:
                logger.warning(f"Exact lookup signal failed: {exc}")

        # 5. Reciprocal Rank Fusion (RRF)
        signal_rankings = {
            "cypher_overlap": cypher_cases,
            "node_search": node_cases,
            "chunk_search": chunk_cases,
            "exact_lookup": exact_cases,
        }
        fused = fuse_signals(signal_rankings)

        # 6. Ask Lane Execution (trident_query) & Agreement Check
        ask_lane_res = None
        ask_cited_cases: list[str] = []
        if search_query:
            try:
                ask_raw = await self.gateway.query(query_text=search_query, top_k=top_k, trace=trace)
                if isinstance(ask_raw, dict):
                    # Resolve cited cases from chunks/provenance
                    chunks = ask_raw.get("chunks", [])
                    for chk in chunks:
                        cid = resolve_case_id(chk)
                        if cid and cid not in exclude_ids and cid not in ask_cited_cases:
                            ask_cited_cases.append(cid)
                    ask_lane_res = AskLaneResult(
                        answer=ask_raw.get("answer"),
                        confidence=ask_raw.get("confidence", 0.85),
                        query_ref=ask_raw.get("query_ref"),
                        cited_case_ids=ask_cited_cases,
                    )
            except Exception as exc:
                logger.warning(f"Ask lane trident_query failed: {exc}")

        # Compute Jaccard overlap between fused candidates and ask lane cited cases
        top_fused_ids = [c[0] for c in fused[:top_k]]
        lane_overlap = 1.0
        if top_fused_ids and ask_cited_cases:
            s_fused = set(top_fused_ids)
            s_ask = set(ask_cited_cases)
            union_len = len(s_fused | s_ask)
            lane_overlap = round(len(s_fused & s_ask) / union_len, 3) if union_len > 0 else 0.0

        # 7. Construct SimilarCase objects enriched with ledger attributes and outcomes
        similar_cases: list[SimilarCase] = []
        prov_mode = "MOCK" if self.gateway.mode == "mock" else ("REPLAY" if self.gateway.mode == "replay" else "MCP")

        for rank_zero, (cid, fused_score, signals) in enumerate(fused[:top_k]):
            case_rec = ledger_service.get_case(cid) or {}
            ev_id = generate_id("EV")
            ev_obj = Evidence(
                evidence_id=ev_id,
                tool="retrieval_fusion",
                provider_id="synapt",
                case_id=cid,
                text_span=f"Historical Case {cid}: {case_rec.get('disruption_type')} affecting {case_rec.get('industry')}. Full recovery: {case_rec.get('full_recovery_days')} days.",
                score=fused_score,
                provenance_mode=prov_mode,
            )
            evidence_store[ev_id] = ev_obj

            sim_case = SimilarCase(
                case_id=cid,
                rank=rank_zero + 1,
                fused_score=fused_score,
                signals=signals,
                why=cypher_whys.get(cid, ["Retrieved via multi-signal fusion"]),
                attributes={
                    "disruption_type": case_rec.get("disruption_type"),
                    "industry": case_rec.get("industry"),
                    "supplier_tier": case_rec.get("supplier_tier"),
                    "supplier_region": case_rec.get("supplier_region"),
                    "supplier_size": case_rec.get("supplier_size"),
                    "has_backup_supplier": case_rec.get("has_backup_supplier"),
                    "disruption_severity": case_rec.get("disruption_severity"),
                },
                outcomes={
                    "production_impact_pct": case_rec.get("production_impact_pct"),
                    "revenue_loss_usd": case_rec.get("revenue_loss_usd"),
                    "response_type": case_rec.get("response_type"),
                    "response_time_days": case_rec.get("response_time_days"),
                    "partial_recovery_days": case_rec.get("partial_recovery_days"),
                    "full_recovery_days": case_rec.get("full_recovery_days"),
                    "permanent_supplier_change": case_rec.get("permanent_supplier_change"),
                },
                evidence_ids=[ev_id],
            )
            similar_cases.append(sim_case)

        return similar_cases, evidence_store, ask_lane_res, lane_overlap, relaxed_filters_history


retrieval_service = RetrievalService()
