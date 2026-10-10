"""Feedback & Continuous Improvement Page.

Allows operators to submit qualitative ratings and report actual real-world outcomes.
Submissions enter the human review queue with status='pending'.
"""

from __future__ import annotations

import streamlit as st

from ui.components.api_client import api_client

st.set_page_config(page_title="Operator Feedback", page_icon="💬", layout="wide")


def main() -> None:
    st.title("💬 Operator Feedback & Actual Outcomes")
    st.markdown(
        """
        Record feedback to improve retrieval accuracy and submit verified post-incident outcomes.
        All submissions enter a **Human Review Queue** and must be approved before triggering retraining.
        """
    )

    tab_rating, tab_outcome = st.tabs(["⭐ Investigation Rating & Corrections", "📈 Record Actual Incident Outcome"])

    with tab_rating:
        with st.form("feedback_rating_form"):
            run_id = st.text_input(
                "Investigation Run ID",
                value=st.session_state.get("current_report", {}).get("run_id", "RUN-DEMO-001"),
            )
            case_id = st.text_input("Associated Case ID (Optional)", value="")

            kind = st.selectbox(
                "Feedback Category",
                options=["relevance", "usefulness", "missing_evidence", "incorrect_fact", "general"],
            )

            rating_val = st.slider("Quality Score (1-5)", min_value=1.0, max_value=5.0, value=4.5, step=0.5)

            comment = st.text_area(
                "Operator Comments / Corrections",
                placeholder="Explain why the recommended playbook or similar cases were helpful or inaccurate...",
            )

            submitted = st.form_submit_button("📤 Submit Feedback")

        if submitted:
            payload = {
                "run_id": run_id,
                "case_id": case_id if case_id.strip() else None,
                "kind": kind,
                "value": rating_val,
                "comment": comment.strip() if comment else None,
            }
            resp = api_client.submit_feedback(payload)
            if "error" in resp:
                st.error(f"Failed to submit feedback: {resp['error']}")
            else:
                st.success(f"✅ Feedback received! ID: `{resp.get('feedback_id')}` (Status: PENDING REVIEW)")
                st.info("The submission has been logged into `review_queue` for administrative review.")

    with tab_outcome:
        st.markdown("#### Post-Incident Operational Outcome Log")
        st.caption("Once an incident concludes, record observed metrics to validate conformal intervals and update model cards.")

        with st.form("feedback_outcome_form"):
            oc_run_id = st.text_input(
                "Investigation Run ID",
                value=st.session_state.get("current_report", {}).get("run_id", "RUN-DEMO-001"),
                key="oc_run_id",
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                act_impact = st.number_input("Actual Production Impact (%)", min_value=0.0, max_value=100.0, value=25.0, step=0.5)
            with c2:
                act_loss = st.number_input("Actual Revenue Loss ($)", min_value=0.0, value=350000.0, step=10000.0)
            with c3:
                act_recovery = st.number_input("Actual Full Recovery Days", min_value=0.0, value=22.0, step=1.0)

            act_response = st.selectbox(
                "Actual Primary Response Executed",
                options=["Dual Sourcing", "Expedited Freight", "Inventory Buffer", "Supplier Assistance", "Production Re-routing"],
            )

            is_simulated = st.checkbox("Mark as Simulated Outcome (for benchmarking)", value=False)

            oc_submitted = st.form_submit_button("💾 Record Observed Outcome")

        if oc_submitted:
            payload = {
                "run_id": oc_run_id,
                "kind": "general",
                "value": act_impact,
                "comment": f"Actual outcome logged: Impact={act_impact}%, Loss=${act_loss:,.0f}, Recovery={act_recovery} days, Response={act_response}. Simulated={is_simulated}",
            }
            resp = api_client.submit_feedback(payload)
            if "error" in resp:
                st.error(f"Failed to log outcome: {resp['error']}")
            else:
                st.success(f"✅ Actual outcome logged! ID: `{resp.get('feedback_id')}` (Status: PENDING REVIEW)")
                st.info("Review queue admin command: `python -m scripts.review_feedback approve --id <queue_id>`")


if __name__ == "__main__":
    main()
