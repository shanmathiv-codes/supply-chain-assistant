"""Tests verifying UI modules import cleanly and page components function without errors."""

from __future__ import annotations

import importlib
import os

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
    fig_text_factors = plot_feature_factors(
        ["tier=1 (elevates estimate by 2.5)", "supplier_region (reduces estimate by 1.2)"],
        "Test Target",
    )
    assert list(fig_text_factors.data[0].x) == [2.5, -1.2]
    assert list(fig_text_factors.data[0].y) == [
        "tier=1 (elevates estimate by 2.5)",
        "supplier_region (reduces estimate by 1.2)",
    ]

    fig_gauge = plot_priority_gauge(78.0, "P2")
    assert fig_gauge is not None


def test_ui_launcher_adds_project_root_to_pythonpath(monkeypatch):
    from scripts import dev

    captured = {}

    def fake_run_cmd(cmd, cwd=dev.ROOT_DIR, env=None):
        captured["env"] = env
        return 0

    monkeypatch.setattr(dev, "run_cmd", fake_run_cmd)
    monkeypatch.setenv("PYTHONPATH", "existing-path")

    assert dev.cmd_ui(None) == 0
    assert str(dev.ROOT_DIR) in captured["env"]["PYTHONPATH"].split(os.pathsep)
    assert "existing-path" in captured["env"]["PYTHONPATH"].split(os.pathsep)


def test_recommendation_display_handles_string_and_list_caveats():
    analysis_page = importlib.import_module("ui.pages.2_Analysis")
    report = {
        "recommendations": [
            {
                "title": "Activate an alternate supplier",
                "action": "Confirm backup supplier capacity.",
                "caveats": "Confirm current supplier availability before execution.",
            },
            {
                "id": "REC-002",
                "action": "Reroute shipments.",
                "caveats": ["Check lane capacity."],
            },
        ]
    }

    markdown = analysis_page.generate_printable_markdown(report)

    assert "### Activate an alternate supplier" in markdown
    assert "- **Action:** Confirm backup supplier capacity." in markdown
    assert "- **Caveat:** Confirm current supplier availability before execution." in markdown
    assert "- **Caveat:** Check lane capacity." in markdown
    assert "Rationale:** None" not in markdown
    assert "Caveat:** H\n" not in markdown


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
