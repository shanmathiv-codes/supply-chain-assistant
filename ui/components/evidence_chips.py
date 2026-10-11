"""Streamlit Evidence Chips Component.

Renders clickable, informative evidence chips linking claims directly to substrate passages.
Uses palette (#b6d4c5, #f7f0e5, #58554e) with zero emojis and flat styling.
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

    chips_html = " ".join(
        [
            (
                "<span style='background:#e3eee8; color:#2f4d3d; border:1px solid #b6d4c5; "
                f"padding:2px 8px; border-radius:3px; font-size:0.82em; font-weight:600;'>[{eid}]</span>"
            )
            for eid in evidence_ids
        ]
    )
    st.markdown(chips_html, unsafe_allow_html=True)

    with st.expander("Cited Substrate Evidence", expanded=False):
        for idx, eid in enumerate(evidence_ids):
            ev_data = evidence_store.get(eid, {})
            tool = ev_data.get("tool", "Substrate Tool")
            prov = ev_data.get("provenance_mode", "MCP")

            if prov == "MCP":
                badge_style = "background:#e3eee8; color:#2f4d3d; border:1px solid #b6d4c5;"
            elif prov == "MOCK":
                badge_style = "background:#f5eee3; color:#6e4f2b; border:1px solid #dfcfb7;"
            else:
                badge_style = "background:#f0ede6; color:#58554e; border:1px solid #dcd5c9;"

            st.markdown(
                f"**{eid}** | `{tool}` "
                f"<span style='{badge_style} padding:2px 6px; border-radius:3px; font-size:0.75em; font-weight:600;'>{prov}</span>",
                unsafe_allow_html=True,
            )
            text_span = (
                ev_data.get("text_span") or ev_data.get("content") or "No text span captured."
            )
            st.markdown(
                f"<div style='background:#ffffff; border-left:3px solid #b6d4c5; padding:8px 12px; margin:6px 0; font-size:0.9em; color:#58554e;'>"
                f'"{text_span}"'
                f"</div>",
                unsafe_allow_html=True,
            )
            if ev_data.get("node_id"):
                st.caption(f"Graph Node ID: `{ev_data.get('node_id')}`")
            if idx < len(evidence_ids) - 1:
                st.divider()
