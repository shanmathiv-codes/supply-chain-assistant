"""Trains regression models for supply chain disruption outcome targets with CV and conformal calibration."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.core.config import load_yaml_config
from ml.training.conformal import SplitConformalPredictor

FEATURES_CONFIG = load_yaml_config("features.yaml")
T0_FEATURES = FEATURES_CONFIG["feature_sets"]["T0"]["columns"]
FORBIDDEN = set(FEATURES_CONFIG.get("forbidden_columns", {}).get("outcome_prediction", []))

SPLITS_DIR = Path("dataset/splits")
MODELS_DIR = Path("artifacts/models")

TARGETS = [
    ("production_impact_pct", False),
    ("revenue_loss_usd", True),  # log1p transformed
    ("full_recovery_days", False),
]


def assert_no_forbidden_columns(feature_cols: list[str], target: str):
    """Enforce integrity rule: forbidden columns must never appear in feature set."""
    forbidden_used = set(feature_cols).intersection(FORBIDDEN)
    if forbidden_used:
        raise ValueError(
            f"Forbidden columns {forbidden_used} detected in features for target {target}!"
        )
    if target in feature_cols:
        raise ValueError(f"Target column {target} cannot be inside its own feature set!")


def get_preprocessor(feature_cols: list[str]) -> ColumnTransformer:
    cat_cols = [c for c in feature_cols if c != "has_backup_supplier"]
    num_cols = [c for c in feature_cols if c == "has_backup_supplier"]

    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
            ("num", "passthrough", num_cols),
        ]
    )


def train_single_target(target: str, use_log1p: bool, evaluate_final: bool = False):
    print(f"\n--- Training Regressors for: {target} ---")
    assert_no_forbidden_columns(T0_FEATURES, target)

    # 1. Load splits
    train_df = pd.read_parquet(SPLITS_DIR / "train.parquet")
    cal_df = pd.read_parquet(SPLITS_DIR / "calibration.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "val.parquet")

    # train_fit = train minus calibration
    cal_ids = set(cal_df["disruption_id"])
    train_fit_df = train_df[~train_df["disruption_id"].isin(cal_ids)].copy()

    # Prepare features and targets
    X_train = train_fit_df[T0_FEATURES].copy()
    y_train = train_fit_df[target].values
    if use_log1p:
        y_train = np.log1p(y_train)

    X_cal = cal_df[T0_FEATURES].copy()
    y_cal = cal_df[target].values
    if use_log1p:
        y_cal = np.log1p(y_cal)

    X_val = val_df[T0_FEATURES].copy()
    y_val = val_df[target].values
    if use_log1p:
        y_val = np.log1p(y_val)

    # 2. Candidate models
    get_preprocessor(T0_FEATURES)
    candidates = {
        "dummy_median": DummyRegressor(strategy="median"),
        "ridge": Ridge(alpha=1.0),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=60, random_state=42),
    }

    kf = KFold(n_splits=3, shuffle=True, random_state=42)
    cv_scores = {}
    best_candidate_name = None
    best_mae = float("inf")

    # Quick 3-fold CV on train_fit sample (subsample for speed if huge)
    sample_size = min(len(X_train), 20000)
    X_cv = X_train.iloc[:sample_size]
    y_cv = y_train[:sample_size]

    for name, model in candidates.items():
        pipe = Pipeline([("preprocessor", get_preprocessor(T0_FEATURES)), ("model", model)])
        fold_maes = []
        for train_idx, test_idx in kf.split(X_cv):
            X_tr, X_te = X_cv.iloc[train_idx], X_cv.iloc[test_idx]
            y_tr, y_te = y_cv[train_idx], y_cv[test_idx]
            pipe.fit(X_tr, y_tr)
            preds = pipe.predict(X_te)
            fold_maes.append(mean_absolute_error(y_te, preds))
        mean_mae = float(np.mean(fold_maes))
        cv_scores[name] = round(mean_mae, 4)
        print(f"  Candidate {name:25s} -> CV MAE: {mean_mae:.4f}")
        if mean_mae < best_mae:
            best_mae = mean_mae
            best_candidate_name = name

    print(f"  Selected Champion: {best_candidate_name}")

    # 3. Train champion on all train_fit
    champion_model = candidates[best_candidate_name]
    final_pipeline = Pipeline(
        [
            ("preprocessor", get_preprocessor(T0_FEATURES)),
            ("model", champion_model),
        ]
    )
    final_pipeline.fit(X_train, y_train)

    # 4. Conformal Calibration on held-out calibration split
    cal_preds = final_pipeline.predict(X_cal)
    conformal = SplitConformalPredictor(nominal_coverage=0.80)
    q_val = conformal.calibrate(y_cal, cal_preds)
    cal_coverage = conformal.evaluate_coverage(y_cal, cal_preds)
    print(
        f"  Conformal Calibrated (80% nominal) -> q_val: {q_val:.4f}, Cal Coverage: {cal_coverage['empirical_coverage']:.1%}"
    )

    # Validate on validation set
    val_preds = final_pipeline.predict(X_val)
    val_coverage = conformal.evaluate_coverage(y_val, val_preds)
    val_mae = mean_absolute_error(y_val, val_preds)
    val_rmse = root_mean_squared_error(y_val, val_preds)
    print(f"  Val MAE: {val_mae:.4f}, Val Coverage: {val_coverage['empirical_coverage']:.1%}")

    # Baseline comparison
    dummy = DummyRegressor(strategy="median")
    dummy.fit(X_train, y_train)
    dummy_val_preds = dummy.predict(X_val)
    baseline_mae = mean_absolute_error(y_val, dummy_val_preds)
    baseline_rmse = root_mean_squared_error(y_val, dummy_val_preds)

    # 5. Final test split evaluation (touched only when evaluate_final is True)
    test_metrics = {}
    if evaluate_final:
        test_df = pd.read_parquet(SPLITS_DIR / "test.parquet")
        X_test = test_df[T0_FEATURES].copy()
        y_test = test_df[target].values
        if use_log1p:
            y_test = np.log1p(y_test)
        test_preds = final_pipeline.predict(X_test)
        test_mae = float(mean_absolute_error(y_test, test_preds))
        test_rmse = float(root_mean_squared_error(y_test, test_preds))
        test_cov = conformal.evaluate_coverage(y_test, test_preds)
        test_metrics = {
            "test_mae": round(test_mae, 4),
            "test_rmse": round(test_rmse, 4),
            "test_empirical_coverage": test_cov["empirical_coverage"],
            "test_mean_width": test_cov["mean_interval_width"],
        }
        print(
            f"  [TEST SPLIT EVALUATION] MAE: {test_mae:.4f}, Coverage: {test_cov['empirical_coverage']:.1%}"
        )

    # 6. Save Model Artifacts
    target_dir = MODELS_DIR / target
    target_dir.mkdir(parents=True, exist_ok=True)
    model_path = target_dir / "model.joblib"
    joblib.dump(final_pipeline, model_path)

    meta = {
        "target": target,
        "champion_algorithm": best_candidate_name,
        "feature_set": "T0",
        "features": T0_FEATURES,
        "use_log1p": use_log1p,
        "conformal_q": round(q_val, 4),
        "nominal_coverage": 0.80,
        "cv_scores": cv_scores,
        "val_metrics": {
            "val_mae": round(float(val_mae), 4),
            "val_rmse": round(float(val_rmse), 4),
            "baseline_mae": round(float(baseline_mae), 4),
            "baseline_rmse": round(float(baseline_rmse), 4),
            "val_empirical_coverage": val_coverage["empirical_coverage"],
        },
        "test_metrics": test_metrics,
        "split_sizes": {
            "train_fit": len(X_train),
            "calibration": len(X_cal),
            "val": len(X_val),
            "test": len(test_df) if evaluate_final else 0,
        },
    }

    meta_path = target_dir / "model_card.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Write Model Card Markdown
    card_md = f"""# Model Card: {target}
**Task:** Regression
**Algorithm:** {best_candidate_name}
**Feature Set:** T0 ({", ".join(T0_FEATURES)})
**Log1p Transform:** {use_log1p}

## Metrics vs Baseline
- Validation MAE: {val_mae:.4f} (Baseline: {baseline_mae:.4f})
- Validation RMSE: {val_rmse:.4f} (Baseline: {baseline_rmse:.4f})
- Beats Median Baseline: {"YES" if val_mae < baseline_mae else "NO"}

## Conformal Uncertainty Calibration
- Nominal Coverage: 80%
- Empirical Coverage (Val): {val_coverage["empirical_coverage"]:.1%}
- Conformal Residual Radius (q): {q_val:.4f}

## Integrity Constraints
- Forbidden columns check: PASSED (no leakages)
- Calibration split: Held-out from model fit
"""
    (target_dir / "model_card.md").write_text(card_md, encoding="utf-8")
    print(f"  Artifacts saved to {target_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train outcome regression models.")
    parser.add_argument(
        "--final", action="store_true", help="Evaluate final model once on test split"
    )
    args = parser.parse_args()

    print("=== Training Supply Chain Disruption Regressors ===")
    for target, use_log1p in TARGETS:
        train_single_target(target, use_log1p, evaluate_final=args.final)
    print("\nAll regression models successfully trained.")


if __name__ == "__main__":
    main()
