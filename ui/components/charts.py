"""Plotly Charts Component for Streamlit UI.

Provides interactive charts for:
- Conformal prediction intervals
- Top impact driving factors (SHAP / Permutation)
- Priority triage score breakdown

Strictly adheres to palette (#b6d4c5, #f7f0e5, #58554e) with flat styling.
"""

from __future__ import annotations

import re
from typing import Any

import plotly.graph_objects as go

# Global chart style constants
COLOR_TAUPE = "#58554e"
COLOR_SAGE = "#b6d4c5"
COLOR_CREAM = "#f7f0e5"
COLOR_BORDER = "#e5ded3"
COLOR_POSITIVE_FACTOR = "#486a58"
COLOR_NEGATIVE_FACTOR = "#8c4a3e"
FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'


def plot_conformal_interval(
    point: float,
    low: float,
    high: float,
    target_name: str,
    unit: str = "%",
) -> go.Figure:
    """Create a horizontal range bar showing point estimate and 80% conformal interval."""
    fig = go.Figure()

    # Range bar (low to high) using sage palette tone
    fig.add_trace(
        go.Bar(
            y=[target_name],
            x=[high - low],
            base=[low],
            orientation="h",
            name="80% Conformal Interval",
            marker=dict(color="#c8ded2", line=dict(color=COLOR_SAGE, width=1)),
            hoverinfo="text",
            hovertext=f"80% Interval: [{low:.1f}{unit}, {high:.1f}{unit}]",
        )
    )

    # Point estimate marker using primary taupe
    fig.add_trace(
        go.Scatter(
            y=[target_name],
            x=[point],
            mode="markers+text",
            name="Point Estimate",
            marker=dict(color=COLOR_TAUPE, size=12, symbol="diamond"),
            text=[f"{point:.1f}{unit}"],
            textposition="top center",
            textfont=dict(color=COLOR_TAUPE, family=FONT_FAMILY, size=12),
            hoverinfo="text",
            hovertext=f"Predicted Point Estimate: {point:.1f}{unit}",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"{target_name} Prediction (80% Conformal Range)",
            font=dict(color=COLOR_TAUPE, family=FONT_FAMILY, size=13),
        ),
        xaxis=dict(
            title=f"Predicted Value ({unit})",
            gridcolor=COLOR_BORDER,
            color=COLOR_TAUPE,
            zerolinecolor=COLOR_BORDER,
        ),
        yaxis=dict(color=COLOR_TAUPE),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        showlegend=False,
        height=180,
        margin=dict(l=20, r=20, t=40, b=30),
    )
    return fig


def plot_feature_factors(factors: list[dict[str, Any] | str], target_name: str) -> go.Figure:
    """Horizontal bar chart of top positive and negative predictive drivers."""
    if not factors:
        fig = go.Figure()
        fig.update_layout(
            title=dict(text="No factor attribution available", font=dict(color=COLOR_TAUPE)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#ffffff",
            height=150,
        )
        return fig

    feature_names = []
    importances = []
    for i, factor in enumerate(factors):
        if isinstance(factor, str):
            feature_names.append(factor)
            match = re.search(r"(?:importance:\s*|estimate by\s*)(-?\d+(?:\.\d+)?)", factor)
            importance = float(match.group(1)) if match else 0.0
            if "reduces estimate by" in factor:
                importance = -abs(importance)
            importances.append(importance)
        else:
            feature_names.append(factor.get("feature", f"Factor {i}"))
            importances.append(factor.get("importance", 0.0))

    # Clean solid colors: elevating estimate is negative/risk factor, reducing is protective
    colors = [
        COLOR_NEGATIVE_FACTOR if v > 0 else COLOR_POSITIVE_FACTOR if v < 0 else "#8a857b"
        for v in importances
    ]

    fig = go.Figure(
        go.Bar(
            x=importances,
            y=feature_names,
            orientation="h",
            marker=dict(color=colors),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"Impact Drivers for {target_name}",
            font=dict(color=COLOR_TAUPE, family=FONT_FAMILY, size=13),
        ),
        xaxis=dict(
            title="Feature Attribution Impact",
            gridcolor=COLOR_BORDER,
            color=COLOR_TAUPE,
            zerolinecolor=COLOR_BORDER,
        ),
        yaxis=dict(color=COLOR_TAUPE),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        height=240,
        margin=dict(l=20, r=20, t=40, b=30),
    )
    return fig


def plot_priority_gauge(score: float, band: str) -> go.Figure:
    """Create a gauge chart for priority score and triage band."""
    colors = {
        "P1": "#8c4a3e",
        "P2": "#ad6a47",
        "P3": "#8a764d",
        "P4": "#486a58",
    }
    bar_color = colors.get(band, COLOR_TAUPE)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={
                "text": f"Triage Priority: <b>{band}</b>",
                "font": {"size": 16, "color": COLOR_TAUPE, "family": FONT_FAMILY},
            },
            number={"font": {"color": COLOR_TAUPE, "family": FONT_FAMILY}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": COLOR_TAUPE,
                    "tickfont": {"color": COLOR_TAUPE},
                },
                "bar": {"color": bar_color},
                "steps": [
                    {"range": [0, 40], "color": "#e3eee8"},
                    {"range": [40, 65], "color": "#f7f0e5"},
                    {"range": [65, 80], "color": "#ede2d5"},
                    {"range": [80, 100], "color": "#f7eae8"},
                ],
                "threshold": {
                    "line": {"color": COLOR_TAUPE, "width": 2},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=230,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
