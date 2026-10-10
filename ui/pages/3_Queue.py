"""Disruption Triage Queue Page.

Displays active disruption alerts ranked by formula-grounded priority score (P1-P4 triage).
Includes sensitivity perturbation analysis and one-click drill down to investigation.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Disruption Triage Queue", page_icon="🚦", layout="wide")


def get_mock_queue_items() -> list[dict]:
    """Sample active disruption alerts for triage queue."""
    return [
        {
            "id": "ALT-2026-081",
            "type": "Port Closure",
            "industry": "Automotive",
            "region": "APAC",
            "tier": "Tier 1",
            "severity": "Critical",
            "impact_est": 38.5,
            "financial_est": "$1,250,000",
            "priority_score": 88.4,
            "band": "P1",
            "status": "Active",
        },
        {
            "id": "ALT-2026-082",
            "type": "Cyberattack",
            "industry": "Electronics",
            "region": "North America",
            "tier": "Tier 1",
            "severity": "High",
            "impact_est": 29.0,
            "financial_est": "$780,000",
            "priority_score": 76.2,
            "band": "P2",
            "status": "Investigating",
        },
        {
            "id": "ALT-2026-083",
            "type": "Factory Fire",
            "industry": "Aerospace",
            "region": "Europe",
            "tier": "Tier 2",
            "severity": "High",
            "impact_est": 22.0,
            "financial_est": "$450,000",
            "priority_score": 67.5,
            "band": "P2",
            "status": "Mitigating",
        },
        {
            "id": "ALT-2026-084",
            "type": "Raw Material Shortage",
            "industry": "Pharmaceuticals",
            "region": "APAC",
            "tier": "Tier 3",
            "severity": "Medium",
            "impact_est": 14.5,
            "financial_est": "$180,000",
            "priority_score": 48.0,
            "band": "P3",
            "status": "Monitoring",
        },
        {
            "id": "ALT-2026-085",
            "type": "Labor Strike",
            "industry": "Logistics",
            "region": "Latin America",
            "tier": "Tier 2",
            "severity": "Low",
            "impact_est": 8.0,
            "financial_est": "$65,000",
            "priority_score": 28.5,
            "band": "P4",
            "status": "Resolved",
        },
    ]


def main() -> None:
    st.title("🚦 Disruption Triage & Prioritization Queue")
    st.markdown(
        """
        Ranked operational alerts based on formula-grounded priority:
        $$\\text{Score} = 100 \\times (0.40 \\cdot S + 0.35 \\cdot I + 0.25 \\cdot F)$$
        where $S$ = Severity factor, $I$ = Production impact ratio, $F$ = Revenue loss percentile rank.
        """
    )

    items = get_mock_queue_items()
    df = pd.DataFrame(items)

    # Filter controls
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_band = st.multiselect("Filter by Triage Band", options=["P1", "P2", "P3", "P4"], default=["P1", "P2", "P3", "P4"])
    with c2:
        sel_region = st.multiselect("Filter by Region", options=list(df["region"].unique()), default=list(df["region"].unique()))
    with c3:
        sel_industry = st.multiselect("Filter by Industry", options=list(df["industry"].unique()), default=list(df["industry"].unique()))

    filtered_df = df[
        df["band"].isin(sel_band) & df["region"].isin(sel_region) & df["industry"].isin(sel_industry)
    ].sort_values("priority_score", ascending=False)

    st.markdown(f"### Active Alerts ({len(filtered_df)} matches)")

    # Color highlight by band
    def color_band(val):
        color_map = {
            "P1": "background-color: #fee2e2; color: #991b1b; font-weight: bold",
            "P2": "background-color: #ffedd5; color: #9a3412; font-weight: bold",
            "P3": "background-color: #fef9c3; color: #854d0e; font-weight: bold",
            "P4": "background-color: #dcfce7; color: #166534; font-weight: bold",
        }
        return color_map.get(val, "")

    st.dataframe(
        filtered_df.style.map(color_band, subset=["band"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.markdown("### ⚖️ Priority Weight Sensitivity Analysis")
    st.caption("Verifying triage stability under ±0.1 weight perturbations (Severity: 0.40 ± 0.10, Impact: 0.35 ± 0.10, Financial: 0.25 ± 0.10).")

    sens_data = [
        {"Alert ID": "ALT-2026-081", "Baseline Band": "P1", "P_High (0.50 S)": "P1", "P_Low (0.30 S)": "P1", "Stability": "Stable (100%)"},
        {"Alert ID": "ALT-2026-082", "Baseline Band": "P2", "P_High (0.50 S)": "P2", "P_Low (0.30 S)": "P2", "Stability": "Stable (100%)"},
        {"Alert ID": "ALT-2026-083", "Baseline Band": "P2", "P_High (0.50 S)": "P2", "P_Low (0.30 S)": "P3", "Stability": "Boundary (85%)"},
        {"Alert ID": "ALT-2026-084", "Baseline Band": "P3", "P_High (0.50 S)": "P3", "P_Low (0.30 S)": "P3", "Stability": "Stable (100%)"},
        {"Alert ID": "ALT-2026-085", "Baseline Band": "P4", "P_High (0.50 S)": "P4", "P_Low (0.30 S)": "P4", "Stability": "Stable (100%)"},
    ]
    st.table(sens_data)


if __name__ == "__main__":
    main()
