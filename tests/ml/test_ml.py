"""Test suite for Machine Learning models, conformal intervals, explainability, and resilience."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ["SYNAPT_MODE"] = "mock"
os.environ["LLM_MODE"] = "fake"

from app.core.config import load_yaml_config, settings

settings.synapt_mode = "mock"
settings.llm_mode = "fake"

from app.main import app
from ml.registry import model_registry
from ml.resilience import compute_resilience_estimate
from ml.training.conformal import SplitConformalPredictor
from ml.training.train_regressors import assert_no_forbidden_columns

client = TestClient(app)
FEATURES_CONFIG = load_yaml_config("features.yaml")


def test_forbidden_columns_integrity():
    """Verify that forbidden columns are strictly rejected from all feature sets."""
    forbidden = FEATURES_CONFIG.get("forbidden_columns", {}).get("outcome_prediction", [])
    t0_cols = FEATURES_CONFIG["feature_sets"]["T0"]["columns"]

    # Assert T0 contains no forbidden columns
    for col in forbidden:
        assert col not in t0_cols

    # Assert helper raises ValueError if forbidden column is injected
    with pytest.raises(ValueError, match="Forbidden columns"):
        assert_no_forbidden_columns(t0_cols + ["partial_recovery_days"], "full_recovery_days")

    with pytest.raises(ValueError, match="Target column"):
        assert_no_forbidden_columns(t0_cols + ["production_impact_pct"], "production_impact_pct")


def test_conformal_interval_calculator():
    """Verify split-conformal calibration and interval coverage arithmetic."""
    conformal = SplitConformalPredictor(nominal_coverage=0.80)
    y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
    y_pred = [11.0, 19.0, 32.0, 42.0, 48.0]

    q = conformal.calibrate(y_true, y_pred)
    assert q >= 2.0

    low, high = conformal.predict_interval(25.0)
    assert low < 25.0 < high
    assert low >= 0.0  # clipped to positive


def test_model_registry_predictions():
    """Verify that model registry loads trained models and outputs valid intervals."""
    profile = {
        "disruption_type": "Labor Strike",
        "industry": "Automotive",
        "supplier_tier": "Tier 1",
        "supplier_region": "North America",
        "supplier_size": "Medium",
        "has_backup_supplier": True,
        "disruption_severity": "High",
    }

    pred_impact = model_registry.predict_target("production_impact_pct", profile)
    assert pred_impact is not None
    assert 0.0 <= pred_impact.point <= 100.0
    assert pred_impact.low <= pred_impact.point <= pred_impact.high
    assert len(pred_impact.top_factors) > 0

    pred_recovery = model_registry.predict_target("full_recovery_days", profile)
    assert pred_recovery is not None
    assert pred_recovery.point >= 1.0
    assert pred_recovery.low <= pred_recovery.point <= pred_recovery.high


def test_analog_divergence_flag():
    """Verify analog divergence check when point prediction exceeds analog bounds."""
    profile = {
        "disruption_type": "Natural Disaster",
        "industry": "Electronics",
        "supplier_tier": "Tier 1",
        "supplier_region": "North America",
        "supplier_size": "Large",
        "has_backup_supplier": False,
        "disruption_severity": "Critical",
    }

    # Pass analog cases where recovery is very low or high
    pred = model_registry.predict_target("full_recovery_days", profile, similar_case_ids=["DIS-000001", "DIS-000002"])
    assert pred is not None
    if pred.analog:
        assert pred.analog.n > 0
        assert isinstance(pred.divergence, bool)


def test_resilience_estimation():
    """Verify resilience index and conditional severity risk calculation."""
    resilience = compute_resilience_estimate(
        predicted_impact_pct=40.0,
        predicted_loss_usd=500000.0,
        predicted_recovery_days=45.0,
        has_backup_supplier=True,
        conditional_severity_prob=0.65,
    )
    assert 0.0 <= resilience.resilience_index <= 100.0
    assert 0.0 <= resilience.conditional_severity_risk <= 1.0
    assert "backup" in resilience.backup_supplier_benefit.lower()
    assert "conditional" in resilience.explanation.lower()


def test_predict_endpoint():
    """Verify POST /disruptions/predict returns predictions, intervals, and resilience."""
    payload = {
        "profile": {
            "disruption_type": "Operational Failure",
            "industry": "Consumer Goods",
            "supplier_tier": "Tier 2",
            "supplier_region": "Europe",
            "supplier_size": "Small",
            "has_backup_supplier": False,
            "disruption_severity": "Medium",
        }
    }
    resp = client.post("/disruptions/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert "resilience" in data
    assert len(data["predictions"]) > 0
    first_pred = data["predictions"][0]
    assert "target" in first_pred
    assert "point" in first_pred
    assert "low" in first_pred
    assert "high" in first_pred
    assert first_pred["nominal_coverage"] == 0.80
