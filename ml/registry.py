"""Model registry managing trained artifacts, conformal intervals, version hashing, and predictions."""

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.logging import logger
from app.schemas.report import AnalogStats, Prediction, ResilienceEstimate
from app.schemas.request import DisruptionProfile
from app.services.ledger import ledger_service
from ml.explain.shap_explain import explain_prediction
from ml.resilience import compute_resilience_estimate

MODELS_DIR = Path("artifacts/models")


class ModelRegistry:
    """Loads trained scikit-learn models, applies conformal bounds, and handles analog divergence checks."""

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.loaded_models: dict[str, Any] = {}
        self.metadata: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, str] = {}
        self._load_all_models()

    def _hash_file(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()[:12]

    def _load_all_models(self):
        if not self.models_dir.exists():
            return
        for target_dir in self.models_dir.iterdir():
            if target_dir.is_dir():
                model_file = target_dir / "model.joblib"
                card_file = target_dir / "model_card.json"
                if model_file.exists():
                    try:
                        self.loaded_models[target_dir.name] = joblib.load(model_file)
                        self.versions[target_dir.name] = self._hash_file(model_file)
                        if card_file.exists():
                            self.metadata[target_dir.name] = json.loads(
                                card_file.read_text(encoding="utf-8")
                            )
                        else:
                            self.metadata[target_dir.name] = {}
                    except Exception as exc:
                        logger.warning(f"Could not load model for {target_dir.name}: {exc}")

    def is_available(self, target: str) -> bool:
        return target in self.loaded_models

    def predict_target(
        self,
        target: str,
        features_dict: dict[str, Any],
        similar_case_ids: list[str] | None = None,
    ) -> Prediction | None:
        if not self.is_available(target):
            return None

        pipe = self.loaded_models[target]
        meta = self.metadata.get(target, {})
        version = self.versions.get(target, "v1.0")
        feature_cols = meta.get("features", list(features_dict.keys()))
        use_log1p = meta.get("use_log1p", False)
        q_val = meta.get("conformal_q", 10.0)

        # Build single-row DataFrame
        row_data = {col: features_dict.get(col, "Unknown") for col in feature_cols}
        if "has_backup_supplier" in row_data:
            row_data["has_backup_supplier"] = bool(row_data["has_backup_supplier"])
        row_df = pd.DataFrame([row_data])

        try:
            raw_pred = float(pipe.predict(row_df)[0])
        except Exception as exc:
            logger.warning(f"Prediction execution failed for {target}: {exc}")
            return None

        # Point and interval calculations
        if use_log1p:
            point = float(np.expm1(raw_pred))
            low = float(np.expm1(max(0.0, raw_pred - q_val)))
            high = float(np.expm1(raw_pred + q_val))
        else:
            point = float(raw_pred)
            low = float(raw_pred - q_val)
            high = float(raw_pred + q_val)

        # Clip values to physically valid bounds
        if target == "production_impact_pct":
            point = min(100.0, max(0.0, point))
            low = min(100.0, max(0.0, low))
            high = min(100.0, max(0.0, high))
        elif target == "revenue_loss_usd":
            point = max(0.0, point)
            low = max(0.0, low)
            high = max(0.0, high)
        elif target == "full_recovery_days":
            point = max(1.0, point)
            low = max(1.0, low)
            high = max(1.0, high)

        # Explainability top factors
        top_factors = explain_prediction(pipe, row_df)

        # Analog comparison stats
        analog_stats = None
        divergence = False
        c_ids = similar_case_ids or []
        if c_ids:
            analog_data = ledger_service.compute_analog_stats(c_ids)
            n_val = analog_data.get("n", 0)
            if n_val > 0:
                p10_val = analog_data.get("p10", 0.0)
                p90_val = analog_data.get("p90", 0.0)
                med_val = analog_data.get("median", 0.0)

                # Check for divergence between model point estimate and analog p10-p90 range
                if point < p10_val or point > p90_val:
                    divergence = True
                    div_warn = f"Model point estimate ({point:.1f}) diverges from analog cohort range [{p10_val:.1f} - {p90_val:.1f}]."
                else:
                    div_warn = None

                analog_stats = AnalogStats(
                    n=n_val,
                    median=med_val,
                    p10=p10_val,
                    p90=p90_val,
                    case_ids=c_ids,
                    divergence_warning=div_warn,
                )

        return Prediction(
            target=target,
            point=round(point, 2),
            low=round(low, 2),
            high=round(high, 2),
            nominal_coverage=0.80,
            model_version=f"{target}@{version}",
            feature_set="T0",
            top_factors=top_factors,
            analog=analog_stats,
            divergence=divergence,
        )

    def predict_all(
        self,
        profile: DisruptionProfile,
        similar_case_ids: list[str] | None = None,
    ) -> tuple[list[Prediction], ResilienceEstimate | None, list[str]]:
        """Compute predictions across all regression outcome targets and resilience estimate."""
        prof_dict = profile.model_dump(exclude_none=True)
        gaps: list[str] = []
        predictions: list[Prediction] = []

        targets = ["production_impact_pct", "revenue_loss_usd", "full_recovery_days"]
        for tgt in targets:
            pred = self.predict_target(tgt, prof_dict, similar_case_ids)
            if pred:
                predictions.append(pred)
            else:
                gaps.append(f"Model estimate unavailable for {tgt}.")

        # Predict conditional severity risk probability if classifier present
        cond_prob = None
        if self.is_available("severity_high_or_critical"):
            try:
                cls_pipe = self.loaded_models["severity_high_or_critical"]
                meta = self.metadata.get("severity_high_or_critical", {})
                f_cols = meta.get("features", list(prof_dict.keys()))
                r_df = pd.DataFrame([{c: prof_dict.get(c, "Unknown") for c in f_cols}])
                cond_prob = float(cls_pipe.predict_proba(r_df)[0][1])
            except Exception as exc:
                logger.warning(f"Severity classifier prediction failed: {exc}")

        # Compute Resilience Estimate
        resilience = None
        if predictions:
            pred_map = {p.target: p.point for p in predictions}
            resilience = compute_resilience_estimate(
                predicted_impact_pct=pred_map.get("production_impact_pct", 35.0),
                predicted_loss_usd=pred_map.get("revenue_loss_usd", 250000.0),
                predicted_recovery_days=pred_map.get("full_recovery_days", 45.0),
                has_backup_supplier=bool(prof_dict.get("has_backup_supplier", False)),
                conditional_severity_prob=cond_prob,
            )

        return predictions, resilience, gaps


model_registry = ModelRegistry()
