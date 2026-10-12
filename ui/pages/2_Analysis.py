"""Analysis & Investigation Report View.

Displays multi-agent disruption investigation reports across tabs:
- Summary
- Similar Cases (4 signals + evidence chips)
- Predictions (split-conformal intervals & feature factors)
- Grounded Recommendations (SOPs & response outcomes)
- Substrate Trace & Fidelity
- Limitations & Gaps
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ui.components.charts import (
    plot_conformal_interval,
    plot_feature_factors,
    plot_priority_gauge,
)
from ui.components.evidence_chips import render_evidence_chips
from ui.components.theme import apply_theme, status_badge

st.set_page_config(page_title="Investigation Analysis", layout="wide")


def get_demo_report() -> dict[str, Any]:
    """Fallback sample report when no live run has been executed yet."""
    return {
        "run_id": "RUN-DEMO-001",
        "status": "ok",
        "runtime_modes": {
            "llm_mode": "fake",
            "synapt_mode": "mock",
            "dataset_source": "synthetic",
        },
        "classification": {
            "disruption_type": "Port Closure",
            "disruption_severity": "High",
            "confidence": 0.88,
            "abstain": False,
        },
        "priority": {
            "score": 78.5,
            "band": "P2",
            "components": {"severity": 0.75, "impact": 0.82, "financial": 0.79},
            "reason": "High severity event affecting critical Tier-1 supplier with significant production exposure.",
        },
        "similar_cases": [
            {
                "case_id": "DIS-00142",
                "rank": 1,
                "fused_score": 0.94,
                "signals": {"cypher_overlap": 1, "node_search": 2, "chunk_search": 1, "exact": 0},
                "why": ["Exact disruption_type match", "Same region (APAC)", "Tier 1 supplier"],
                "attributes": {
                    "disruption_type": "Port Closure",
                    "industry": "Automotive",
                    "supplier_region": "APAC",
                    "supplier_tier": "Tier 1",
                },
                "outcomes": {
                    "production_impact_pct": 28.5,
                    "revenue_loss_usd": 380000,
                    "full_recovery_days": 24,
                    "response_type": "Dual Sourcing",
                },
                "evidence_ids": ["EVD-001", "EVD-002"],
            },
            {
                "case_id": "DIS-00388",
                "rank": 2,
                "fused_score": 0.88,
                "signals": {"cypher_overlap": 2, "node_search": 1, "chunk_search": 3, "exact": 0},
                "why": ["Same region and industry", "Expedited freight response executed"],
                "attributes": {
                    "disruption_type": "Port Closure",
                    "industry": "Automotive",
                    "supplier_region": "APAC",
                    "supplier_tier": "Tier 1",
                },
                "outcomes": {
                    "production_impact_pct": 32.0,
                    "revenue_loss_usd": 420000,
                    "full_recovery_days": 29,
                    "response_type": "Expedited Freight",
                },
                "evidence_ids": ["EVD-003"],
            },
        ],
        "predictions": [
            {
                "target": "production_impact_pct",
                "point": 26.4,
                "low": 18.5,
                "high": 34.3,
                "nominal_coverage": 0.80,
                "model_version": "champion-hgb-v1",
                "top_factors": [
                    {"feature": "supplier_tier=Tier 1", "importance": 4.2},
                    {"feature": "has_backup_supplier=Yes", "importance": -3.8},
                    {"feature": "region=APAC", "importance": 2.1},
                ],
                "analog": {"n": 14, "median": 28.5, "p10": 19.0, "p90": 36.0},
                "divergence": False,
            },
            {
                "target": "full_recovery_days",
                "point": 25.0,
                "low": 17.0,
                "high": 33.0,
                "nominal_coverage": 0.80,
                "model_version": "champion-hgb-v1",
                "top_factors": [
                    {"feature": "severity=High", "importance": 6.1},
                    {"feature": "has_backup_supplier=Yes", "importance": -5.4},
                ],
                "analog": {"n": 14, "median": 24.0, "p10": 15.0, "p90": 32.0},
                "divergence": False,
            },
        ],
        "recommendations": [
            {
                "id": "REC-001",
                "action": "Activate pre-contracted secondary supplier in APAC lane",
                "rationale": "Historical analogs activating secondary sourcing recovered 8.5 days faster than freight rerouting alone.",
                "evidence_ids": ["EVD-001"],
                "caveats": [
                    "Associational historical pattern; actual performance contingent on supplier line availability."
                ],
            },
            {
                "id": "REC-002",
                "action": "Initiate expedited air-freight buffer for critical subcomponents",
                "rationale": "Mitigates short-term production line starvation while port customs backlogs clear.",
                "evidence_ids": ["EVD-003"],
                "caveats": ["Cost-benefit depends on value-density of stalled shipments."],
            },
        ],
        "claims": [
            {
                "text": "Historical port closure events in APAC with Tier 1 suppliers show median recovery of 24 days.",
                "kind": "HISTORICAL_FACT",
                "evidence_ids": ["EVD-001", "EVD-002"],
            },
            {
                "text": "Dual sourcing response is associated with an average 8.5-day reduction in downtime.",
                "kind": "DATASET_STATISTIC",
                "evidence_ids": ["EVD-001"],
            },
        ],
        "evidence": {
            "EVD-001": {
                "tool": "trident_query",
                "provider_id": "supply_chain_disruption",
                "provenance_mode": "MOCK",
                "text_span": "Case DIS-00142: High severity port closure in APAC resolved in 24 days using Dual Sourcing.",
            },
            "EVD-002": {
                "tool": "trident_cypher",
                "provider_id": "supply_chain_disruption",
                "provenance_mode": "MOCK",
                "text_span": "attr_overlap_rank query identified 14 shared attribute cases in segment APAC/Automotive/Tier1.",
            },
            "EVD-003": {
                "tool": "trident_get_chunks",
                "provider_id": "supply_chain_disruption",
                "provenance_mode": "MOCK",
                "text_span": "Case DIS-00388 narrative: Expedited freight maintained 70% production continuity during harbor congestion.",
            },
        },
        "substrate_trace": [
            {"tool": "trident_query", "latency_ms": 145, "rows": 1, "ok": True},
            {"tool": "trident_cypher", "latency_ms": 82, "rows": 14, "ok": True},
            {"tool": "trident_get_chunks", "latency_ms": 110, "rows": 5, "ok": True},
        ],
        "knowledge_gaps": [],
        "limitations": [
            "Mock substrate adapter active; results simulated from local ledger and cards.",
            "Estimates reflect statistical associations and do not assert deterministic causality.",
        ],
    }


def generate_printable_markdown(report: dict[str, Any]) -> str:
    """Generate clean printable markdown document from the report."""
    run_id = report.get("run_id", "N/A")
    status = report.get("status", "N/A").upper()
    prio = report.get("priority", {})
    clf = report.get("classification", {})

    md = f"""# Supply Chain Disruption Investigation Report: {run_id}

**Status:** {status} | **Priority:** {prio.get("band", "N/A")} (Score: {prio.get("score", 0):.1f})
**Classification:** {clf.get("disruption_severity", "N/A")} {clf.get("disruption_type", "N/A")} (Confidence: {clf.get("confidence", 0):.2f})

---

## 1. Executive Summary
{prio.get("reason", "Operational disruption triage summary.")}

## 2. Predictions & Conformal Intervals (80% Nominal Coverage)
"""
    for p in report.get("predictions", []):
        md += f"- **{p.get('target')}**: Point Estimate **{p.get('point'):.1f}** (80% Range: [{p.get('low'):.1f}, {p.get('high'):.1f}])\n"

    md += "\n## 3. Recommended Actions\n"
    for idx, r in enumerate(report.get("recommendations", []), 1):
        title = r.get("title") or r.get("id") or f"Recommendation {idx}"
        md += f"### {title}\n"
        if r.get("action"):
            md += f"- **Action:** {r.get('action')}\n"
        if r.get("rationale"):
            md += f"- **Rationale:** {r.get('rationale')}\n"
        if r.get("evidence_ids"):
            md += f"- **Citations:** {', '.join(r.get('evidence_ids'))}\n"
        for caveat in _recommendation_caveats(r):
            md += f"- **Caveat:** {caveat}\n"

    md += "\n## 4. Limitations & Non-Causal Disclaimers\n"
    for lim in report.get("limitations", []):
        md += f"- {lim}\n"

    return md


def _recommendation_caveats(recommendation: dict[str, Any]) -> list[str]:
    """Normalize current string caveats and older list-shaped reports for display."""
    caveats = recommendation.get("caveats")
    if isinstance(caveats, str):
        return [caveats] if caveats else []
    if isinstance(caveats, list):
        return [caveat for caveat in caveats if isinstance(caveat, str) and caveat]
    return []


def main() -> None:
    apply_theme()

    st.title("Disruption Investigation Report")

    report = st.session_state.get("current_report")
    if not report:
        st.info("No active investigation report loaded. Displaying baseline reference scenario.")
        report = get_demo_report()

    run_id = report.get("run_id", "UNKNOWN")
    status = report.get("status", "ok").upper()
    priority = report.get("priority", {})
    evidence_store = report.get("evidence", {})

    # Top header bar aligned
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        st.subheader(f"Run ID: `{run_id}`")
    with c2:
        st.metric("Status", status)
    with c3:
        st.metric(
            "Triage Priority",
            priority.get("band", "N/A"),
            delta=f"Score: {priority.get('score', 0):.1f}",
        )
    with c4:
        st.download_button(
            "Export JSON",
            data=json.dumps(report, indent=2),
            file_name=f"report_{run_id}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Export Markdown",
            data=generate_printable_markdown(report),
            file_name=f"report_{run_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    tab_summary, tab_cases, tab_preds, tab_recs, tab_trace, tab_limits = st.tabs(
        [
            "Summary",
            "Similar Cases",
            "Predictions & Intervals",
            "Grounded Response",
            "Substrate Trace",
            "Limitations & Gaps",
        ]
    )

    # TAB 1: SUMMARY
    with tab_summary:
        st.markdown("### Executive Incident Summary")
        col_gauge, col_details = st.columns([1, 2])

        with col_gauge:
            fig_prio = plot_priority_gauge(priority.get("score", 50.0), priority.get("band", "P2"))
            st.plotly_chart(fig_prio, use_container_width=True)

        with col_details:
            st.markdown(f"**Triage Rationale:** {priority.get('reason', 'Standard triage')}")
            clf = report.get("classification", {})
            st.markdown(
                f"- **Classified Profile:** {clf.get('disruption_severity')} {clf.get('disruption_type')}"
            )
            st.markdown(f"- **Classification Confidence:** {clf.get('confidence', 0.0) * 100:.1f}%")

            st.markdown("#### Key Verified Claims")
            for claim in report.get("claims", []):
                kind_badge = status_badge(claim.get("kind", "CLAIM"), variant="cream")
                st.markdown(f"- {kind_badge} {claim.get('text')}", unsafe_allow_html=True)
                render_evidence_chips(
                    claim.get("evidence_ids", []), evidence_store, key_prefix="sum"
                )

    # TAB 2: SIMILAR CASES
    with tab_cases:
        st.markdown("### Analog Disruption Cases Retrieved via 4-Signal Hybrid Fusion")
        cases = report.get("similar_cases", [])
        if not cases:
            st.warning("No similar historical cases found in the knowledge base.")
        else:
            for c in cases:
                with st.container():
                    col_info, col_outcomes = st.columns([2, 1])
                    with col_info:
                        st.markdown(
                            f"#### Rank #{c.get('rank')} — Case `{c.get('case_id')}` (Fused Score: {c.get('fused_score', 0):.2f})"
                        )
                        st.caption("Why Matched: " + " • ".join(c.get("why", [])))
                        attrs = c.get("attributes", {})
                        st.write(
                            f"**Profile:** {attrs.get('supplier_tier')} | {attrs.get('supplier_region')} | {attrs.get('industry')}"
                        )
                        render_evidence_chips(
                            c.get("evidence_ids", []),
                            evidence_store,
                            key_prefix=f"case_{c.get('case_id')}",
                        )

                    with col_outcomes:
                        st.markdown("**Historical Outcomes:**")
                        out = c.get("outcomes", {})
                        st.markdown(
                            f"- Production Impact: **{out.get('production_impact_pct', 'N/A')}%**"
                        )
                        st.markdown(f"- Revenue Loss: **${out.get('revenue_loss_usd', 0):,.0f}**")
                        st.markdown(
                            f"- Full Recovery: **{out.get('full_recovery_days', 'N/A')} days**"
                        )
                        st.markdown(f"- Response Used: `{out.get('response_type', 'N/A')}`")
                    st.divider()

    # TAB 3: PREDICTIONS
    with tab_preds:
        st.markdown("### Machine Learning Predictions & 80% Conformal Calibration")
        preds = report.get("predictions", [])
        if not preds:
            st.info("No ML predictions available for this scenario.")
        else:
            for p in preds:
                tgt = p.get("target", "Target")
                unit = "%" if "pct" in tgt else " days" if "days" in tgt else " USD"
                c_chart, c_shap = st.columns([1, 1])

                with c_chart:
                    fig_interval = plot_conformal_interval(
                        point=p.get("point", 0.0),
                        low=p.get("low", 0.0),
                        high=p.get("high", 0.0),
                        target_name=tgt,
                        unit=unit,
                    )
                    st.plotly_chart(fig_interval, use_container_width=True)

                    analog = p.get("analog", {})
                    if analog:
                        st.caption(
                            f"Historical Analog Range (n={analog.get('n', 0)}): "
                            f"Median = {analog.get('median', 0):.1f}{unit} | P10-P90 = [{analog.get('p10', 0):.1f}, {analog.get('p90', 0):.1f}]"
                        )
                    if p.get("divergence"):
                        st.warning(
                            "Analog Divergence Alert: Model prediction deviates from historical analog distribution."
                        )

                with c_shap:
                    fig_factors = plot_feature_factors(p.get("top_factors", []), tgt)
                    st.plotly_chart(fig_factors, use_container_width=True)
                st.divider()

    # TAB 4: RECOMMENDATIONS
    with tab_recs:
        st.markdown("### Grounded Response Recommendations")
        recs = report.get("recommendations", [])
        if not recs:
            st.warning("No recommendations generated (degraded mode or insufficient evidence).")
        else:
            for idx, r in enumerate(recs, 1):
                title = r.get("title") or r.get("action") or f"Recommendation {idx}"
                st.markdown(f"#### {idx}. {title}")
                if r.get("title") and r.get("action") and r["title"] != r["action"]:
                    st.markdown(f"**Action:** {r['action']}")
                if r.get("rationale"):
                    st.markdown(f"**Rationale:** {r['rationale']}")
                render_evidence_chips(
                    r.get("evidence_ids", []), evidence_store, key_prefix=f"rec_{idx}"
                )
                for cav in _recommendation_caveats(r):
                    st.caption(f"*Caveat:* {cav}")
                st.divider()

    # TAB 5: SUBSTRATE TRACE
    with tab_trace:
        st.markdown("### Substrate Gateway Execution Trace")
        trace = report.get("substrate_trace", [])
        if not trace:
            st.caption("No substrate calls recorded.")
        else:
            st.table(trace)

    # TAB 6: LIMITATIONS & GAPS
    with tab_limits:
        st.markdown("### Scientific Integrity & Boundary Disclaimers")
        limits = report.get("limitations", [])
        for lim in limits:
            st.warning(lim)
        gaps = report.get("knowledge_gaps", [])
        if gaps:
            st.markdown("#### Identified Knowledge Gaps")
            for gap in gaps:
                st.info(f"• {gap}")


if __name__ == "__main__":
    main()
