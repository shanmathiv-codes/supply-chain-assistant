"""Trains classification models for conditional severity risk and supplier change probability."""
import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.core.config import load_yaml_config

FEATURES_CONFIG = load_yaml_config("features.yaml")
SPLITS_DIR = Path("dataset/splits")
MODELS_DIR = Path("artifacts/models")


def train_single_classifier(target_name: str, evaluate_final: bool = False):
    print(f"\n--- Training Classifier for: {target_name} ---")

    train_df = pd.read_parquet(SPLITS_DIR / "train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "val.parquet")

    # Define features and binary target
    if target_name == "severity_high_or_critical":
        features = [
            "disruption_type",
            "industry",
            "supplier_tier",
            "supplier_region",
            "supplier_size",
            "has_backup_supplier",
        ]
        y_train = train_df["disruption_severity"].isin(["High", "Critical"]).astype(int).values
        y_val = val_df["disruption_severity"].isin(["High", "Critical"]).astype(int).values
    else:  # permanent_supplier_change
        features = [
            "disruption_type",
            "industry",
            "supplier_tier",
            "supplier_region",
            "supplier_size",
            "has_backup_supplier",
            "disruption_severity",
        ]
        y_train = train_df["permanent_supplier_change"].astype(int).values
        y_val = val_df["permanent_supplier_change"].astype(int).values

    X_train = train_df[features].copy()
    X_val = val_df[features].copy()

    cat_cols = [c for c in features if c != "has_backup_supplier"]
    num_cols = [c for c in features if c == "has_backup_supplier"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
            ("num", "passthrough", num_cols),
        ]
    )

    model = HistGradientBoostingClassifier(max_iter=50, random_state=42)
    pipe = Pipeline([("preprocessor", preprocessor), ("model", model)])

    pipe.fit(X_train, y_train)

    val_preds = pipe.predict(X_val)
    val_probs = pipe.predict_proba(X_val)[:, 1]

    val_acc = float(accuracy_score(y_val, val_preds))
    val_f1 = float(f1_score(y_val, val_preds, average="macro"))
    val_auc = float(roc_auc_score(y_val, val_probs))

    print(f"  Val Accuracy: {val_acc:.4f}, Macro-F1: {val_f1:.4f}, AUC-ROC: {val_auc:.4f}")

    target_dir = MODELS_DIR / target_name
    target_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, target_dir / "model.joblib")

    meta = {
        "target": target_name,
        "algorithm": "HistGradientBoostingClassifier",
        "features": features,
        "val_metrics": {
            "accuracy": round(val_acc, 4),
            "macro_f1": round(val_f1, 4),
            "roc_auc": round(val_auc, 4),
        },
        "split_sizes": {
            "train": len(X_train),
            "val": len(X_val),
        },
    }
    (target_dir / "model_card.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    card_md = f"""# Model Card: {target_name}
**Task:** Binary Classification
**Algorithm:** HistGradientBoostingClassifier
**Features:** {', '.join(features)}

## Validation Performance
- Accuracy: {val_acc:.4f}
- Macro F1: {val_f1:.4f}
- ROC-AUC: {val_auc:.4f}
"""
    (target_dir / "model_card.md").write_text(card_md, encoding="utf-8")
    print(f"  Artifacts saved to {target_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train classification models.")
    parser.add_argument("--final", action="store_true", help="Evaluate final model once on test split")
    args = parser.parse_args()

    print("=== Training Supply Chain Disruption Classifiers ===")
    for target in ["severity_high_or_critical", "permanent_supplier_change"]:
        train_single_classifier(target, evaluate_final=args.final)
    print("\nAll classification models successfully trained.")


if __name__ == "__main__":
    main()
