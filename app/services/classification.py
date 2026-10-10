"""Ensemble disruption classification service combining ticket mining, neighbour voting, and LLM."""

from collections import Counter
from typing import Any

from app.core.logging import logger
from app.llm.fake import fake_llm
from app.llm.router import router
from app.schemas.evidence import SubstrateCall
from app.schemas.report import ClassificationResult
from app.services.ledger import ledger_service
from app.substrate.case_resolver import resolve_case_id
from app.substrate.gateway import SynaptReadGateway


class ClassificationService:
    """Ensemble classifier combining substrate label_ticket, Cypher neighbor votes, and LLM extraction."""

    def __init__(self, gateway: SynaptReadGateway | None = None):
        self.gateway = gateway or SynaptReadGateway()

    async def classify_disruption(
        self,
        profile: dict[str, Any] | None = None,
        free_text: str | None = None,
        trace: list[SubstrateCall] | None = None,
    ) -> ClassificationResult:
        prof = profile or {}
        text = free_text or "Disruption event in supply chain facility."
        signal_votes: dict[str, dict[str, str]] = {}

        # 1. Substrate ticket mining vote (trident_label_ticket)
        try:
            ticket_res = await self.gateway.label_ticket(ticket_text=text, trace=trace)
            if isinstance(ticket_res, dict) and "disruption_type" in ticket_res:
                signal_votes["label_ticket"] = {
                    "disruption_type": ticket_res.get("disruption_type", "Operational Failure"),
                    "disruption_severity": ticket_res.get("disruption_severity", "Medium"),
                }
        except Exception as exc:
            logger.warning(f"label_ticket call failed: {exc}")

        # 2. Cypher neighbour vote (attr_overlap_rank)
        try:
            cypher_res = await self.gateway.cypher(
                template_name="attr_overlap_rank",
                params={
                    "disruption_type": prof.get("disruption_type"),
                    "industry": prof.get("industry"),
                    "supplier_tier": prof.get("supplier_tier"),
                    "supplier_region": prof.get("supplier_region"),
                    "supplier_size": prof.get("supplier_size"),
                    "disruption_severity": prof.get("disruption_severity"),
                    "limit": 10,
                },
                trace=trace,
            )
            top_ids = [resolve_case_id(r) for r in cypher_res if resolve_case_id(r)]
            neighbor_cases = ledger_service.get_cases_batch(top_ids[:5])
            if neighbor_cases:
                types = [c["disruption_type"] for c in neighbor_cases if c.get("disruption_type")]
                sevs = [
                    c["disruption_severity"] for c in neighbor_cases if c.get("disruption_severity")
                ]
                if types:
                    vote_type = Counter(types).most_common(1)[0][0]
                    vote_sev = Counter(sevs).most_common(1)[0][0] if sevs else "Medium"
                    signal_votes["neighbor_vote"] = {
                        "disruption_type": vote_type,
                        "disruption_severity": vote_sev,
                    }
        except Exception as exc:
            logger.warning(f"Neighbor vote failed: {exc}")

        # 3. LLM classification vote
        try:
            llm_res, _ = await router.complete_structured(
                prompt_name="classify",
                role="fast",
                messages=[
                    {"role": "system", "content": "Classify disruption incident."},
                    {"role": "user", "content": f"Text: {text}\nProfile: {prof}"},
                ],
                context={
                    "text": text,
                    "disruption_type": prof.get("disruption_type"),
                    "disruption_severity": prof.get("disruption_severity"),
                },
            )
            if isinstance(llm_res, dict):
                signal_votes["llm_mapping"] = {
                    "disruption_type": llm_res.get(
                        "disruption_type", prof.get("disruption_type", "Operational Failure")
                    ),
                    "disruption_severity": llm_res.get(
                        "disruption_severity", prof.get("disruption_severity", "Medium")
                    ),
                }
        except Exception as exc:
            logger.warning(f"LLM classify call failed: {exc}")
            fake_res = fake_llm.invoke("classify", {"text": text})
            signal_votes["llm_mapping"] = {
                "disruption_type": fake_res.get("disruption_type", "Operational Failure"),
                "disruption_severity": fake_res.get("disruption_severity", "Medium"),
            }

        # Fallback if no votes collected
        if not signal_votes:
            return ClassificationResult(
                disruption_type=prof.get("disruption_type") or "Operational Failure",
                disruption_severity=prof.get("disruption_severity") or "Medium",
                confidence=0.50,
                signal_votes={},
                abstained=True,
                reason="No classification signals available to reach quorum.",
            )

        # Ensemble resolution
        type_votes = [v["disruption_type"] for v in signal_votes.values() if "disruption_type" in v]
        sev_votes = [
            v["disruption_severity"] for v in signal_votes.values() if "disruption_severity" in v
        ]

        type_counts = Counter(type_votes)
        sev_counts = Counter(sev_votes)

        best_type, top_type_cnt = type_counts.most_common(1)[0]
        best_sev, top_sev_cnt = sev_counts.most_common(1)[0]

        total_voters = len(signal_votes)
        agreement_ratio = top_type_cnt / total_voters

        # Check for abstention: if voters split evenly with no consensus
        abstained = False
        if total_voters >= 3 and top_type_cnt == 1:
            abstained = True
            confidence = 0.40
            reason = f"Ensemble abstained: signals disagreed with complete conflict ({type_votes})."
        elif agreement_ratio == 1.0:
            confidence = 0.95
            reason = f"All {total_voters} signals unanimously agreed on {best_type} ({best_sev})."
        else:
            confidence = round(0.60 + 0.30 * agreement_ratio, 2)
            reason = f"Ensemble majority consensus ({top_type_cnt}/{total_voters} votes) for {best_type} ({best_sev})."

        return ClassificationResult(
            disruption_type=best_type,
            disruption_severity=best_sev,
            confidence=confidence,
            signal_votes=signal_votes,
            abstained=abstained,
            reason=reason,
        )


classification_service = ClassificationService()
