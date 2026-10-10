"""Tests verifying UI modules import cleanly and page components function without errors."""

from __future__ import annotations

import importlib

import pytest


def test_ui_components_import():
    """Verify all UI components import cleanly."""
    from ui.components.api_client import UIAPIClient, api_client
    from ui.components.charts import (
        plot_conformal_interval,
        plot_feature_factors,
        plot_priority_gauge,
    )

    assert api_client is not None
    assert isinstance(api_client, UIAPIClient)

    # Test chart generators return valid plotly figures
    fig_ci = plot_conformal_interval(25.0, 18.0, 32.0, "Production Impact", "%")
    assert fig_ci is not None

    fig_shap = plot_feature_factors([{"feature": "tier=1", "importance": 2.5}], "Test Target")
    assert fig_shap is not None

    fig_gauge = plot_priority_gauge(78.0, "P2")
    assert fig_gauge is not None


def test_ui_pages_syntax_and_imports():
    """Verify all Streamlit page scripts can be compiled and imported without syntax errors."""
    pages = [
        "ui.app",
        "ui.pages.1_New_Disruption",
        "ui.pages.2_Analysis",
        "ui.pages.3_Queue",
        "ui.pages.4_Feedback",
        "ui.pages.5_Quality",
    ]

    for page_mod in pages:
        try:
            mod = importlib.import_module(page_mod)
            assert mod is not None
        except Exception as e:
            pytest.fail(f"Failed to import UI module '{page_mod}': {e}")
