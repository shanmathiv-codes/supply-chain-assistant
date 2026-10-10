"""Deterministic fake LLM engine generating schema-faithful mock outputs."""
from typing import Any

from app.core.guardrails import map_or_validate_category


class FakeLLM:
    """Provides deterministic responses for all system prompt templates without network access."""

    def invoke(self, prompt_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Dispatch prompt execution to deterministic templating handlers."""
        clean_name = prompt_name.replace("_v1", "").strip()
        if clean_name == "response":
            clean_name = "response_plan"
        handler_name = f"_handle_{clean_name}"
        handler = getattr(self, handler_name, self._handle_default)
        return handler(context)

    def _handle_intake(self, ctx: dict[str, Any]) -> dict[str, Any]:
        text = ctx.get("text", "")
        lower = text.lower()

        # Regex heuristic
        d_type = None
        for cand in ["natural disaster", "labor strike", "operational failure", "cyber incident", "bankruptcy"]:
            if cand in lower:
                d_type, _, _ = map_or_validate_category("disruption_type", cand)
                break
        if not d_type:
            d_type = "Operational Failure"

        sev = "Medium"
        if "critical" in lower or "catastrophic" in lower:
            sev = "Critical"
        elif "high" in lower or "severe" in lower:
            sev = "High"
        elif "low" in lower or "minor" in lower:
            sev = "Low"

        ind = "Automotive" if "car" in lower or "auto" in lower else "Electronics"
        tier = "Tier 1" if "tier 1" in lower or "primary" in lower else "Tier 2"

        return {
            "disruption_type": d_type,
            "industry": ind,
            "supplier_tier": tier,
            "supplier_region": "North America",
            "supplier_size": "Medium",
            "has_backup_supplier": "backup" in lower,
            "disruption_severity": sev,
            "observed_production_impact_pct": 35.0 if "impact" in lower else None,
            "observed_revenue_loss_usd": 500000.0 if "loss" in lower else None,
            "missing_fields": [],
            "summary": f"Extracted {sev} {d_type} affecting {ind} {tier} supplier.",
        }

    def _handle_classify(self, ctx: dict[str, Any]) -> dict[str, Any]:
        d_type = ctx.get("disruption_type") or "Operational Failure"
        sev = ctx.get("disruption_severity") or "Medium"
        return {
            "disruption_type": d_type,
            "disruption_severity": sev,
            "confidence": 0.88,
            "reason": f"Classified as {d_type} ({sev}) based on matching substrate signals and profile text.",
        }

    def _handle_response_plan(self, ctx: dict[str, Any]) -> dict[str, Any]:
        evidence_ids = ctx.get("evidence_ids", ["EV-MOCK-001"])
        return {
            "recommendations": [
                {
                    "title": "Activate Alternate Sourcing & Logistics Buffering",
                    "action": "Engage secondary suppliers and shift near-term shipment allocations to mitigate capacity loss.",
                    "evidence_ids": evidence_ids[:2],
                    "source_type": "historical_case",
                    "expected_full_recovery_days": 42.0,
                    "historical_cases_count": 12,
                    "caveats": "Historical associations indicate 35-50 days recovery under similar multi-region events.",
                },
                {
                    "title": "Implement Daily Production Rescheduling",
                    "action": "Realign plant manufacturing shifts to accommodate delayed component deliveries.",
                    "evidence_ids": evidence_ids[:1],
                    "source_type": "procedure",
                    "expected_full_recovery_days": 38.0,
                    "historical_cases_count": 8,
                    "caveats": "Requires immediate operations war-room coordination.",
                },
            ]
        }

    def _handle_recovery(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "estimated_trajectory_summary": "Historical recovery profiles exhibit staged restoration: response initiation at 3 days, partial operations at 21 days, full baseline restoration at 45 days.",
            "backup_supplier_impact": "Facilities with active backup supplier agreements historically restored full production 18.5 days faster.",
            "key_milestones_days": {
                "response_initiation": 3.0,
                "partial_recovery": 21.0,
                "full_recovery": 45.0,
            },
            "recurring_risks": [
                "Secondary freight delays during rerouting",
                "Tier 2 raw material availability constraints",
            ],
            "uncertainty_notes": "Recovery estimates carry +/- 12 days variance depending on regional infrastructure recovery.",
        }

    def _handle_synthesize(self, ctx: dict[str, Any]) -> dict[str, Any]:
        ev_ids = ctx.get("evidence_ids", ["EV-MOCK-001"])
        return {
            "narrative_summary": "Disruption analysis complete. Operations team should prioritize alternate supplier activation and production rescheduling.",
            "claims": [
                {
                    "claim_id": "CLM-001",
                    "text": "Historical cases in the automotive sector experienced a median recovery duration of 42.0 days.",
                    "kind": "HISTORICAL_FACT",
                    "evidence_ids": ev_ids[:1],
                },
                {
                    "claim_id": "CLM-002",
                    "text": "Predicted production impact is estimated at 38.5% capacity loss [80% conformal interval: 26.0% - 51.0%].",
                    "kind": "MODEL_ESTIMATE",
                    "evidence_ids": [],
                },
            ],
            "knowledge_gaps": ["No supplier balance sheet data available."],
            "limitations": ["Analysis generated in FAKE LLM mode; verify recommendations before execution."],
        }

    def _handle_judge(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            "scores": {
                "relevance": 5,
                "grounding": 4,
                "actionability": 4,
                "uncertainty": 5,
                "consistency": 5,
            },
            "overall_score": 4.6,
            "passed": True,
            "fix_list": [],
            "reason": "All claims cited valid evidence, intervals included, and uncertainty disclosed appropriately.",
        }

    def _handle_default(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "message": "Default fake LLM response"}


fake_llm = FakeLLM()
