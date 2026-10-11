"""UI Theme and Design System for Supply Chain Disruption Assistant.

Defines the primary palette:
- Sage accent: #b6d4c5
- Warm cream background / surface: #f7f0e5
- Deep slate / taupe text and primary structure: #58554e
"""

from __future__ import annotations

import streamlit as st

THEME_CSS = """
<style>
/* Main typography and colors */
html, body, [class*="css"] {
    color: #58554e;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* App Background */
.stApp {
    background-color: #faf7f2;
}

/* Header decoration */
header[data-testid="stHeader"] {
    background-color: #faf7f2;
    border-bottom: 1px solid #e5ded3;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #f7f0e5;
    border-right: 1px solid #e5ded3;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e5ded3;
    border-radius: 4px;
    padding: 12px 16px;
    box-shadow: none;
}
div[data-testid="stMetricLabel"] {
    color: #58554e;
    font-size: 0.85rem;
    font-weight: 500;
}
div[data-testid="stMetricValue"] {
    color: #58554e;
    font-weight: 600;
}

/* Buttons */
button[kind="primary"] {
    background-color: #58554e !important;
    color: #f7f0e5 !important;
    border: 1px solid #58554e !important;
    border-radius: 4px !important;
    box-shadow: none !important;
    font-weight: 500 !important;
}
button[kind="primary"]:hover {
    background-color: #44423d !important;
    border-color: #44423d !important;
}
button[kind="secondary"] {
    background-color: #f7f0e5 !important;
    color: #58554e !important;
    border: 1px solid #dcd5c9 !important;
    border-radius: 4px !important;
    box-shadow: none !important;
}
button[kind="secondary"]:hover {
    background-color: #ece5d8 !important;
    border-color: #c9bfb0 !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #58554e !important;
    border-radius: 0px !important;
    font-weight: 500 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    border-bottom: 2px solid #58554e !important;
    color: #58554e !important;
}

/* Alerts / Callouts */
div[data-testid="stAlert"] {
    border-radius: 4px;
    border: 1px solid #e5ded3;
    box-shadow: none;
    background-color: #f7f0e5;
    color: #58554e;
}

/* Form containers */
div[data-testid="stForm"] {
    border: 1px solid #e5ded3;
    border-radius: 4px;
    background-color: #ffffff;
    padding: 20px;
}

/* Expander */
div[data-testid="stExpander"] {
    border: 1px solid #e5ded3;
    border-radius: 4px;
    background-color: #ffffff;
    box-shadow: none;
}

/* Clean cards */
.custom-card {
    background-color: #ffffff;
    border: 1px solid #e5ded3;
    border-radius: 4px;
    padding: 16px;
    margin-bottom: 12px;
}

.custom-card-header {
    font-size: 0.95rem;
    font-weight: 600;
    color: #58554e;
    margin-bottom: 8px;
    border-bottom: 1px solid #f0ede6;
    padding-bottom: 6px;
}

/* Badges */
.badge-solid {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0.02em;
}
.badge-sage {
    background-color: #e3eee8;
    color: #2f4d3d;
    border: 1px solid #b6d4c5;
}
.badge-cream {
    background-color: #f7f0e5;
    color: #58554e;
    border: 1px solid #dcd5c9;
}
.badge-taupe {
    background-color: #58554e;
    color: #f7f0e5;
    border: 1px solid #58554e;
}
.badge-warning {
    background-color: #f5eee3;
    color: #6e4f2b;
    border: 1px solid #dfcfb7;
}
.badge-critical {
    background-color: #f7eae8;
    color: #7c3226;
    border: 1px solid #d9b4ae;
}
</style>
"""


def apply_theme() -> None:
    """Inject unified design system stylesheet into the Streamlit page."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def status_badge(text: str, variant: str = "sage") -> str:
    """Return an HTML snippet for a clean solid status badge."""
    allowed = ["sage", "cream", "taupe", "warning", "critical"]
    css_class = f"badge-{variant}" if variant in allowed else "badge-cream"
    return f"<span class='badge-solid {css_class}'>{text}</span>"
