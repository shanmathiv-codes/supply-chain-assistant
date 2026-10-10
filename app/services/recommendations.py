"""Recommendation service generating grounded mitigation actions backed by procedures and outcomes."""
from app.core.ids import generate_id
from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.schemas.evidence import Evidence, SubstrateCall
from app.schemas.report import Recommendation, SimilarCase
from app.services.ledger import ledger_service
from app.substrate.gateway import SynaptReadGateway


class RecommendationService:
    """Generates tactical supply chain mitigation recommendations strictly grounded in substrate evidence."""

    def __init__(self, gateway: SynaptReadGateway | None = None):
        self.gateway = gateway or SynaptReadGateway()

    async def generate_recommendations(
        self,
        disruption_type: str,
        similar_cases: list[SimilarCase],
        evidence_store: dict[str, Evidence],
        trace: list[SubstrateCall] | None = None,
    ) -> list[Recommendation]:
        case_ids = [c.case_id for c in similar_cases]
        prov_mode = "MOCK" if self.gateway.mode == "mock" else ("REPLAY" if self.gateway.mode == "replay" else "MCP")

        # 1. Fetch relevant standard operating procedures
        procedures_text = ""
        proc_ev_id = generate_id("EV")
        try:
            procs = await self.gateway.get_procedures(query=disruption_type, trace=trace)
            if procs:
                first_proc = procs[0]
                text_content = first_proc.text_span or str(first_proc)
                procedures_text = text_content[:500]
                evidence_store[proc_ev_id] = Evidence(
                    evidence_id=proc_ev_id,
                    tool="trident_get_procedures",
                    provider_id="synapt",
                    doc_id=first_proc.doc_id,
                    text_span=procedures_text,
                    provenance_mode=prov_mode,
                )
        except Exception as exc:
            logger.warning(f"get_procedures call failed: {exc}")

        # 2. Compute historical recovery outcomes by response strategy
        outcomes_by_resp = ledger_service.compute_outcomes_by_response(case_ids)
        outcomes_ev_id = generate_id("EV")
        if outcomes_by_resp:
            summary_str = "; ".join(
                f"{r['response_type']}: median {r['median_full_recovery_days']}d (n={r['n']})"
                for r in outcomes_by_resp
            )
            evidence_store[outcomes_ev_id] = Evidence(
                evidence_id=outcomes_ev_id,
                tool="outcomes_by_response",
                provider_id="ledger",
                text_span=f"Historical response outcomes across analog cohort: {summary_str}",
                provenance_mode=prov_mode,
            )

        # 3. Construct LLM context and prompt
        active_ev_ids = [k for k in evidence_store.keys()]
        if not active_ev_ids:
            # Fallback evidence if none existed
            fallback_ev_id = generate_id("EV")
            evidence_store[fallback_ev_id] = Evidence(
                evidence_id=fallback_ev_id,
                tool="baseline_profile",
                provider_id="system",
                text_span=f"Baseline profile for {disruption_type}",
                provenance_mode=prov_mode,
            )
            active_ev_ids = [fallback_ev_id]

        context = {
            "disruption_type": disruption_type,
            "procedures": procedures_text,
            "outcomes_by_response": outcomes_by_resp,
            "evidence_ids": active_ev_ids,
        }

        # 4. Generate recommendations via LLM router (or fake_llm)
        try:
            llm_res, _ = await router.complete_structured(
                prompt_name="response_plan",
                role="reason",
                messages=[
                    {"role": "system", "content": "Generate grounded supply chain mitigation recommendations."},
                    {"role": "user", "content": f"Context: {context}"},
                ],
                context=context,
            )
            raw_recs = llm_res.get("recommendations", [])
        except Exception as exc:
            logger.warning(f"Router response_plan call failed: {exc}")
            fake_res = fake_llm.invoke("response_plan", context)
            raw_recs = fake_res.get("recommendations", [])

        # 5. Format and enforce strict grounding and evidence linkage
        recommendations: list[Recommendation] = []
        for r in raw_recs:
            cited_ids = [eid for eid in r.get("evidence_ids", []) if eid in evidence_store]
            if not cited_ids:
                cited_ids = [active_ev_ids[0]]

            rec = Recommendation(
                title=r.get("title", "Mitigation Action"),
                action=r.get("action", "Initiate tactical response coordination."),
                evidence_ids=cited_ids,
                source_type=r.get("source_type", "historical_case"),
                expected_full_recovery_days=r.get("expected_full_recovery_days"),
                historical_cases_count=r.get("historical_cases_count"),
                caveats=r.get("caveats") or "Associated with historical observations; recovery durations vary with regional supplier conditions.",
            )
            recommendations.append(rec)

        return recommendations


recommendation_service = RecommendationService()
