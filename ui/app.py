"""Supply Chain Disruption Assistant - Main Streamlit Application."""

from __future__ import annotations

import truststore

truststore.inject_into_ssl()

import streamlit as st

from ui.components.api_client import api_client
from ui.components.theme import apply_theme, status_badge

st.set_page_config(
    page_title="Supply Chain Disruption Assistant",
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
        variant = "sage" if api_status in ("HEALTHY", "OK") else "critical"
        st.markdown(
            f"**API Status:** {status_badge(api_status, variant=variant)}",
            unsafe_allow_html=True,
        )
    with col2:
        variant = "sage" if llm_mode == "LIVE" else "cream"
        st.markdown(
            f"**LLM Mode:** {status_badge(llm_mode, variant=variant)}",
            unsafe_allow_html=True,
        )
    with col3:
        variant = "sage" if synapt_mode == "MCP" else "cream"
        st.markdown(
            f"**Substrate:** {status_badge(synapt_mode, variant=variant)}",
            unsafe_allow_html=True,
        )
    with col4:
        variant = "sage" if dataset_source == "REAL" else "cream"
        st.markdown(
            f"**Dataset:** {status_badge(f'{dataset_source} DATA', variant=variant)}",
            unsafe_allow_html=True,
        )

    if synapt_mode == "MOCK" or llm_mode == "FAKE":
        st.markdown(
            "<div style='background:#f7f0e5; border:1px solid #dcd5c9; border-radius:4px; padding:10px 14px; margin-top:12px; font-size:0.9rem; color:#58554e;'>"
            "<strong>Development Notice:</strong> The assistant is running with offline fallbacks "
            "(Mock Substrate and Fake LLM). Historical evidence and predictions are deterministic simulations."
            "</div>",
            unsafe_allow_html=True,
        )
    st.divider()


def main() -> None:
    apply_theme()

    # Check API health
    health = api_client.check_health()

    if health.get("status") == "offline":
        st.error(
            f"FastAPI Backend Offline: Unable to connect to `{api_client.base_url}`.\n\n"
            f"Ensure the API service is running: `python -m scripts.dev api`"
        )
        if st.button("Retry Connection"):
            st.rerun()
        st.stop()

    render_runtime_modes_banner(health)

    st.title("Supply Chain Disruption Investigation System")
    st.markdown(
        """
        Welcome to the **Synapt-Powered Multi-Agent Disruption Investigation Assistant**.

        This system automates end-to-end operational disruption triage, analog evidence retrieval,
        ML impact estimation with split-conformal calibration, and grounded response planning.
        """
    )

    st.markdown("### Operational Modules")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown(
            """
            <div class="custom-card">
                <div class="custom-card-header">1. Disruption Intake & Analysis</div>
                <p style="font-size:0.88rem; line-height:1.5; color:#58554e; margin-bottom:12px;">
                    Structured taxonomic intake and narrative parsing feeding a 9-node multi-agent verification graph.
                    Enforces strict citation grounding against historical case cards.
                </p>
                <div style="font-size:0.8rem; color:#58554e; font-weight:600;">
                    Select <strong>New Disruption</strong> or <strong>Analysis</strong> in the sidebar.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            """
            <div class="custom-card">
                <div class="custom-card-header">2. ML Prediction & Prioritization</div>
                <p style="font-size:0.88rem; line-height:1.5; color:#58554e; margin-bottom:12px;">
                    Distribution-free split-conformal prediction intervals with 80% coverage guarantees.
                    Includes deterministic P1-P4 triage scoring and permutation impact attributions.
                </p>
                <div style="font-size:0.8rem; color:#58554e; font-weight:600;">
                    Select <strong>Queue</strong> in the sidebar to review active disruptions.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_c:
        st.markdown(
            """
            <div class="custom-card">
                <div class="custom-card-header">3. Continuous Improvement & Audit</div>
                <p style="font-size:0.88rem; line-height:1.5; color:#58554e; margin-bottom:12px;">
                    Human-in-the-loop review queue for post-incident outcome logging.
                    Transparent quality dashboards with DeepEval metrics, ablations, and substrate telemetry.
                </p>
                <div style="font-size:0.8rem; color:#58554e; font-weight:600;">
                    Select <strong>Feedback</strong> or <strong>Quality</strong> in the sidebar.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
