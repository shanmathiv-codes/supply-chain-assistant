"""Supply Chain Disruption Assistant - Main Streamlit Application."""

from __future__ import annotations

import streamlit as st

from ui.components.api_client import api_client

st.set_page_config(
    page_title="Supply Chain Disruption Assistant",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_runtime_modes_banner(health_data: dict) -> None:
    """Render persistent runtime operational modes banner at the top of the app."""
    modes = health_data.get("runtime_modes", {})
    llm_mode = modes.get("llm_mode", "fake").upper()
    synapt_mode = modes.get("synapt_mode", "mock").upper()
    dataset_source = modes.get("dataset_source", "synthetic").upper()
    api_status = health_data.get("status", "healthy").upper()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"**API Status:** <span style='background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:12px; font-weight:600;'>● {api_status}</span>",
            unsafe_allow_html=True,
        )
    with col2:
        llm_color = "#dcfce7; color:#15803d" if llm_mode == "LIVE" else "#fef9c3; color:#854d0e"
        st.markdown(
            f"**LLM Mode:** <span style='background:{llm_color}; padding:2px 8px; border-radius:12px; font-weight:600;'>{llm_mode}</span>",
            unsafe_allow_html=True,
        )
    with col3:
        synapt_color = "#dcfce7; color:#15803d" if synapt_mode == "MCP" else "#ffedd5; color:#9a3412"
        st.markdown(
            f"**Substrate:** <span style='background:{synapt_color}; padding:2px 8px; border-radius:12px; font-weight:600;'>{synapt_mode}</span>",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"**Dataset:** <span style='background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:12px; font-weight:600;'>{dataset_source} DATA</span>",
            unsafe_allow_html=True,
        )

    if synapt_mode == "MOCK" or llm_mode == "FAKE":
        st.info(
            "ℹ️ **Development Notice:** The assistant is currently running with offline fallbacks "
            "(Mock Substrate and Fake LLM). Historical evidence and predictions are deterministic simulations.",
            icon="ℹ️",
        )
    st.divider()


def main() -> None:
    # Check API health
    health = api_client.check_health()

    if health.get("status") == "offline":
        st.error(
            f"⚠️ **FastAPI Backend Offline:** Unable to connect to `{api_client.base_url}`.\n\n"
            f"Ensure the API service is running: `python -m scripts.dev api`"
        )
        if st.button("🔄 Retry Connection"):
            st.rerun()
        st.stop()

    render_runtime_modes_banner(health)

    st.title("🚢 Supply Chain Disruption Investigation System")
    st.markdown(
        """
        Welcome to the **Synapt-Powered Multi-Agent Disruption Investigation Assistant**.

        This system automates end-to-end operational disruption triage, analog evidence retrieval,
        ML impact estimation with split-conformal calibration, and grounded response planning.
        """
    )

    st.markdown("### 🧭 Available Capabilities")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("#### 1. Disruption Intake & Analysis")
        st.markdown(
            "- **Intake:** Dynamic taxonomy selectors and unstructured narrative parser.\n"
            "- **Multi-Agent Workflow:** 9-node LangGraph graph with deterministic verification.\n"
            "- **Evidence Grounding:** 100% citation grounding against historical case cards."
        )
        st.markdown("👉 *Navigate to **New Disruption** or **Analysis** in the sidebar.*")

    with col_b:
        st.markdown("#### 2. ML Prediction & Prioritization")
        st.markdown(
            "- **Split-Conformal Intervals:** 80% distribution-free coverage on Impact and Recovery.\n"
            "- **P1-P4 Triage:** Formula-grounded score with sensitivity perturbation checks.\n"
            "- **Explainability:** Top positive and negative feature impact attributions."
        )
        st.markdown("👉 *Navigate to **Queue** to view prioritized active incidents.*")

    with col_c:
        st.markdown("#### 3. Continuous Improvement & Audit")
        st.markdown(
            "- **Human Review Loop:** User feedback rating and actual outcome recording.\n"
            "- **Quality Benchmarks:** DeepEval scores, ablation comparison, and substrate trace.\n"
            "- **Integrity:** Non-causal associations and transparent limitation reporting."
        )
        st.markdown("👉 *Navigate to **Feedback** and **Quality** in the sidebar.*")


if __name__ == "__main__":
    main()
