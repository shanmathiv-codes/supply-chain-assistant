"""Feature set loader and forbidden feature validator."""

from typing import Literal

from app.core.config import load_yaml_config

FEATURES_CONFIG = load_yaml_config("features.yaml")


def get_feature_set(tier: Literal["T0", "T1", "T2"] = "T0") -> list[str]:
    """Retrieve column list for given feature information tier."""
    spec = FEATURES_CONFIG.get("feature_sets", {}).get(tier, {})
    cols = spec.get("columns", [])
    if not cols:
        raise ValueError(f"Feature set {tier} not defined in features.yaml")
    return list(cols)


def get_forbidden_columns(target_name: str | None = None) -> set[str]:
    """Return set of columns forbidden from outcome prediction feature sets."""
    forbidden = set(
        FEATURES_CONFIG.get("forbidden_columns", {}).get(
            "outcome_prediction",
            [
                "partial_recovery_days",
                "response_time_days",
                "permanent_supplier_change",
            ],
        )
    )
    if target_name:
        forbidden.add(target_name)
    return forbidden


def validate_feature_columns(features: list[str], target: str) -> bool:
    """Validate that features contain no target leakage or forbidden outcome fields.
    Raises ValueError on violation.
    """
    forbidden = get_forbidden_columns(target)
    violating = [c for c in features if c in forbidden]
    if violating:
        raise ValueError(
            f"Feature set contains forbidden columns for target '{target}': {violating}"
        )
    return True
