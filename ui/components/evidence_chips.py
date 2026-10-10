"""Streamlit Evidence Chips Component.

Renders clickable, informative evidence chips linking claims directly to substrate passages.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_evidence_chips(
    evidence_ids: list[str],
    evidence_store: dict[str, Any],
    key_prefix: str = "ev",
) -> None:
    """Render interactive evidence chips in Streamlit."""
    if not evidence_ids:
        st.caption("No specific substrate citations associated.")
        return

    chips_html = " ".join([
        f"<span style='background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:12px; font-size:0.85em; font-weight:600;'>📎 {eid}</span>"
        for eid in evidence_ids
    ])
    st.markdown(chips_html, unsafe_allow_html=True)

    with st.expander("🔍 View Cited Substrate Evidence", expanded=False):
        for idx, eid in enumerate(evidence_ids):
            ev_data = evidence_store.get(eid, {})
            tool = ev_data.get("tool", "Substrate Tool")
            prov = ev_data.get("provenance_mode", "MCP")
            badge_color = "#10b981" if prov == "MCP" else "#f59e0b" if prov == "MOCK" else "#3b82f6"

            st.markdown(
                f"**{eid}** — `{tool}` "
                f"<span style='background:{badge_color}; color:white; padding:2px 6px; border-radius:4px; font-size:0.75em;'>{prov}</span>",
                unsafe_allow_html=True,
            )
            text_span = ev_data.get("text_span") or ev_data.get("content") or "No text span captured."
            st.info(f'"{text_span}"')
            if ev_data.get("node_id"):
                st.caption(f"Graph Node ID: `{ev_data.get('node_id')}`")
            if idx < len(evidence_ids) - 1:
                st.divider()
