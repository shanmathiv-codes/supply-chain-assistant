"""New Disruption Intake Page.

Enables supply chain operators to submit structured or free-text disruption alerts
for immediate multi-agent triage and investigation.
"""

from __future__ import annotations

import streamlit as st

from ui.components.api_client import api_client

st.set_page_config(page_title="New Disruption Intake", page_icon="📝", layout="wide")


def main() -> None:
    st.title("📝 New Disruption Intake & Triage")
    st.markdown("Submit operational incident metadata and free-text notes for automated multi-agent analysis.")

    with st.form("disruption_intake_form"):
        col1, col2 = st.columns(2)

        with col1:
            disruption_type = st.selectbox(
                "Disruption Type",
                options=[
                    "Port Closure",
                    "Factory Fire",
                    "Labor Strike",
                    "Cyberattack",
                    "Natural Disaster",
                    "Raw Material Shortage",
                    "Geopolitical Conflict",
                    "Transportation Delay",
                ],
                index=0,
            )
            disruption_severity = st.selectbox(
                "Disruption Severity",
                options=["Low", "Medium", "High", "Critical"],
                index=2,
            )
            industry = st.selectbox(
                "Affected Industry",
                options=[
                    "Automotive",
                    "Aerospace",
                    "Electronics",
                    "Pharmaceuticals",
                    "Retail",
                    "Energy",
                    "Logistics",
                ],
                index=0,
            )
            supplier_region = st.selectbox(
                "Supplier Region",
                options=["APAC", "North America", "Europe", "Latin America", "Middle East"],
                index=0,
            )

        with col2:
            supplier_tier = st.selectbox(
                "Supplier Tier",
                options=["Tier 1", "Tier 2", "Tier 3"],
                index=0,
            )
            supplier_size = st.selectbox(
                "Supplier Size",
                options=["Small", "Medium", "Large"],
                index=2,
            )
            has_backup_supplier = st.radio(
                "Backup Supplier Contracted?",
                options=["Yes", "No"],
                index=0,
                horizontal=True,
            )

        st.markdown("#### Incident Narrative & Operator Notes")
        free_text = st.text_area(
            "Free-text description (Optional - intake will extract missing attributes and cross-reference knowledge graph)",
            value="Urgent alert: Typhoon warning in East Asia causing port closure and halting container departures for Tier 1 supplier.",
            height=100,
            max_chars=2000,
        )

        submitted = st.form_submit_button("🚀 Run Multi-Agent Investigation", use_container_width=True)

    if submitted:
        payload = {
            "profile": {
                "disruption_type": disruption_type,
                "disruption_severity": disruption_severity,
                "industry": industry,
                "supplier_region": supplier_region,
                "supplier_tier": supplier_tier,
                "supplier_size": supplier_size,
                "has_backup_supplier": has_backup_supplier,
            },
            "free_text": free_text.strip() if free_text else None,
        }

        with st.spinner("Executing LangGraph investigation nodes (Intake -> Classify -> Retrieval -> ML -> Verification)..."):
            resp = api_client.analyze_disruption(payload)

        if resp.get("status") == "offline" or resp.get("status") == "error":
            st.error(f"❌ Analysis Failed: {resp.get('message', 'Unknown error')}")
            if resp.get("error_code") == "INJECTION_SUSPECTED":
                st.warning("Security Guardrail: Input text rejected due to suspected prompt injection.")
            elif resp.get("error_code") == "OFF_TOPIC":
                st.warning("Security Guardrail: Input text rejected as out-of-scope for supply chain operations.")
        else:
            st.session_state["current_report"] = resp
            st.success(f"✅ Investigation Complete! Report generated: `{resp.get('run_id')}` (Status: {resp.get('status', 'OK').upper()})")
            st.info("💡 Switch to the **Analysis** page in the sidebar to view full evidence, conformal intervals, and response playbooks.")


if __name__ == "__main__":
    main()
