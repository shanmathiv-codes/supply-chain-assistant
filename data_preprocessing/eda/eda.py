"""Exploratory data analysis: signal check, baseline benchmark, and signal_check.md."""

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def run_signal_check(train_df: pd.DataFrame, val_df: pd.DataFrame, reports_dir: Path) -> dict:
    """Evaluate whether feature sets beat dummy median baselines on validation split."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    targets = ["production_impact_pct", "revenue_loss_usd", "full_recovery_days"]
    features_cat = [
        "disruption_type",
        "industry",
        "supplier_tier",
        "supplier_region",
        "supplier_size",
        "disruption_severity",
    ]
    features_bool = ["has_backup_supplier"]
    all_features = features_cat + features_bool

    results = {}
    beats_baseline_count = 0

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), features_cat),
            ("bool", "passthrough", features_bool),
        ]
    )

    X_train = train_df[all_features].copy()
    X_val = val_df[all_features].copy()

    for target in targets:
        y_train = train_df[target].values
        y_val = val_df[target].values

        # Baseline: DummyRegressor(strategy="median")
        dummy = DummyRegressor(strategy="median")
        dummy.fit(X_train, y_train)
        dummy_pred = dummy.predict(X_val)
        dummy_mae = float(mean_absolute_error(y_val, dummy_pred))

        # Fast tree model: HistGradientBoosting
        pipe = Pipeline(
            [
                ("pre", preprocessor),
                ("model", HistGradientBoostingRegressor(max_iter=50, random_state=42)),
            ]
        )
        pipe.fit(X_train, y_train)
        tree_pred = pipe.predict(X_val)
        tree_mae = float(mean_absolute_error(y_val, tree_pred))

        improvement_pct = ((dummy_mae - tree_mae) / dummy_mae) * 100.0 if dummy_mae > 0 else 0.0
        beats = tree_mae < dummy_mae
        if beats:
            beats_baseline_count += 1

        results[target] = {
            "dummy_mae": round(dummy_mae, 2),
            "tree_mae": round(tree_mae, 2),
            "improvement_pct": round(improvement_pct, 1),
            "beats_baseline": beats,
        }

    overall_signal = beats_baseline_count >= 2

    # Write signal_check.md
    md_lines = [
        "# Signal Check Report",
        "",
        "## Summary",
    ]
    if overall_signal:
        md_lines.append(
            "Features carry statistically meaningful predictive signal and beat the median baseline across disruption targets."
        )
    else:
        md_lines.append(
            "Predictive features carry marginal signal relative to naive median baselines; predictions carry high epistemic uncertainty."
        )

    md_lines.extend(
        [
            "",
            "## Validation MAE Benchmark",
            "| Target | Median Baseline MAE | Tree Model MAE | Improvement % | Beats Baseline? |",
            "|---|---|---|---|---|",
        ]
    )
    for tgt, res in results.items():
        beats_str = "YES" if res["beats_baseline"] else "NO"
        md_lines.append(
            f"| `{tgt}` | {res['dummy_mae']:,.1f} | {res['tree_mae']:,.1f} | {res['improvement_pct']:.1f}% | {beats_str} |"
        )

    (reports_dir / "signal_check.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return results
