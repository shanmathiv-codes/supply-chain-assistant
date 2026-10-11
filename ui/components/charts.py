"""Plotly Charts Component for Streamlit UI.

Provides interactive charts for:
- Conformal prediction intervals
- Top impact driving factors (SHAP / Permutation)
- Priority triage score breakdown
- Ablation experiment comparison
"""

from __future__ import annotations

import re
from typing import Any

import plotly.graph_objects as go


def plot_conformal_interval(
    point: float,
    low: float,
    high: float,
    target_name: str,
    unit: str = "%",
) -> go.Figure:
    """Create a horizontal range bar showing point estimate and 80% conformal interval."""
    fig = go.Figure()

    # Range bar (low to high)
    fig.add_trace(
        go.Bar(
            y=[target_name],
            x=[high - low],
            base=[low],
            orientation="h",
            name="80% Conformal Interval",
            marker=dict(color="rgba(59, 130, 246, 0.3)"),
            hoverinfo="text",
            hovertext=f"80% Interval: [{low:.1f}{unit}, {high:.1f}{unit}]",
        )
    )

    # Point estimate marker
    fig.add_trace(
        go.Scatter(
            y=[target_name],
            x=[point],
            mode="markers+text",
            name="Point Estimate",
            marker=dict(color="rgb(37, 99, 235)", size=14, symbol="diamond"),
            text=[f"{point:.1f}{unit}"],
            textposition="top center",
            hoverinfo="text",
            hovertext=f"Predicted Point Estimate: {point:.1f}{unit}",
        )
    )

    fig.update_layout(
        title=f"{target_name} Prediction with 80% Conformal Range",
        xaxis_title=f"Predicted Value ({unit})",
        showlegend=False,
        height=180,
        margin=dict(l=20, r=20, t=40, b=30),
    )
    return fig


def plot_feature_factors(factors: list[dict[str, Any] | str], target_name: str) -> go.Figure:
    """Horizontal bar chart of top positive and negative predictive drivers."""
    if not factors:
        fig = go.Figure()
        fig.update_layout(title="No factor attribution available", height=150)
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

    colors = ["#ef4444" if v > 0 else "#10b981" if v < 0 else "#94a3b8" for v in importances]

    fig = go.Figure(
        go.Bar(
            x=importances,
            y=feature_names,
            orientation="h",
            marker_color=colors,
        )
    )

    fig.update_layout(
        title=f"Key Impact Drivers for {target_name}",
        xaxis_title="Feature Attribution Impact",
        height=240,
        margin=dict(l=20, r=20, t=40, b=30),
    )
    return fig


def plot_priority_gauge(score: float, band: str) -> go.Figure:
    """Create a gauge chart for priority score and triage band."""
    colors = {
        "P1": "#dc2626",
        "P2": "#ea580c",
        "P3": "#eab308",
        "P4": "#16a34a",
    }
    bar_color = colors.get(band, "#2563eb")

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": f"Triage Priority: <b>{band}</b>", "font": {"size": 20}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": bar_color},
                "steps": [
                    {"range": [0, 40], "color": "rgba(22, 163, 74, 0.15)"},
                    {"range": [40, 65], "color": "rgba(234, 179, 8, 0.15)"},
                    {"range": [65, 80], "color": "rgba(234, 88, 12, 0.15)"},
                    {"range": [80, 100], "color": "rgba(220, 38, 38, 0.15)"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=20))
    return fig
