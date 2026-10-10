"""Tests for the data pipeline: cleaning, splits, cards, forbidden features, and manifest."""

import json
from pathlib import Path

import pandas as pd
import pytest

from data_preprocessing.case_cards.builder import format_single_card
from data_preprocessing.data_cleaning.cleaners import normalize_categoricals, resolve_columns
from data_preprocessing.data_cleaning.validators import validate_and_filter_rows
from data_preprocessing.preprocessing.feature_sets import get_feature_set, validate_feature_columns

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
MINI_CSV = FIXTURES_DIR / "mini_dataset.csv"


def test_mini_dataset_cleaning_and_validation(tmp_path):
    assert MINI_CSV.exists(), "mini_dataset.csv fixture not found"
    df = pd.read_csv(MINI_CSV)
    assert len(df) == 60

    reports_dir = tmp_path / "reports"
    resolved = resolve_columns(df, reports_dir)
    normalized = normalize_categoricals(resolved)
    clean_df, rejected_df = validate_and_filter_rows(normalized, reports_dir)

    assert len(clean_df) > 0
    assert len(clean_df) + len(rejected_df) == 60
    assert "disruption_id" in clean_df.columns
    assert (reports_dir / "column_mapping.json").exists()


def test_card_format_determinism():
    row = {
        "disruption_id": "DIS-99999",
        "disruption_type": "Labor Strike",
        "industry": "Automotive",
        "supplier_tier": "Tier 1",
        "supplier_region": "North America",
        "supplier_size": "Medium",
        "has_backup_supplier": True,
        "disruption_severity": "High",
        "production_impact_pct": 52.0,
        "revenue_loss_usd": 1250000.0,
        "response_type": "Activate Backup Supplier",
        "response_time_days": 3.0,
        "partial_recovery_days": 14.0,
        "full_recovery_days": 42.0,
        "permanent_supplier_change": False,
    }
    card_1 = format_single_card(row)
    card_2 = format_single_card(row)
    assert card_1 == card_2
    assert "## Case DIS-99999" in card_1
    assert "high-severity labor strike" in card_1.lower()
    assert "medium-sized tier 1 supplier" in card_1.lower()


def test_forbidden_features_leakage():
    t0_features = get_feature_set("T0")
    # For target full_recovery_days, T0 should be valid
    assert validate_feature_columns(t0_features, "full_recovery_days")

    # If forbidden column like partial_recovery_days or target is added, validation must fail
    leaked_features = t0_features + ["partial_recovery_days"]
    with pytest.raises(ValueError) as exc:
        validate_feature_columns(leaked_features, "full_recovery_days")
    assert "partial_recovery_days" in str(exc.value)


def test_splits_and_sample_disjointness():
    splits_dir = Path("dataset/splits")
    if not (splits_dir / "train_ids.json").exists():
        pytest.skip("Splits not yet computed in workspace")

    train_ids = set(json.loads((splits_dir / "train_ids.json").read_text(encoding="utf-8")))
    val_ids = set(json.loads((splits_dir / "val_ids.json").read_text(encoding="utf-8")))
    test_ids = set(json.loads((splits_dir / "test_ids.json").read_text(encoding="utf-8")))

    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)

    sample_file = Path("dataset/synapt_sample/sample_ids.json")
    if sample_file.exists():
        sample_ids = set(json.loads(sample_file.read_text(encoding="utf-8")))
        assert sample_ids.issubset(train_ids)
        assert sample_ids.isdisjoint(val_ids)
        assert sample_ids.isdisjoint(test_ids)
