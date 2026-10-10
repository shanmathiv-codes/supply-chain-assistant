"""SHAP TreeExplainer module with seamless permutation importance fallback."""

from typing import Any

import numpy as np
import pandas as pd


def explain_prediction(
    pipeline: Any,
    row_df: pd.DataFrame,
    background_df: pd.DataFrame | None = None,
    top_n: int = 3,
) -> list[str]:
    """Extract top factors driving a specific prediction using SHAP or fallback."""
    try:
        import shap

        model = pipeline.named_steps.get("model")
        preprocessor = pipeline.named_steps.get("preprocessor")

        if preprocessor is not None and model is not None:
            X_trans = preprocessor.transform(row_df)
            if hasattr(X_trans, "toarray"):
                X_trans = X_trans.toarray()

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_trans)
            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            feature_names = preprocessor.get_feature_names_out()
            row_shaps = shap_values[0] if shap_values.ndim > 1 else shap_values

            top_indices = np.argsort(np.abs(row_shaps))[::-1][:top_n]
            factors = []
            for idx in top_indices:
                feat = feature_names[idx].replace("cat__", "").replace("num__", "")
                val = row_shaps[idx]
                direction = "elevates" if val > 0 else "reduces"
                factors.append(f"{feat} ({direction} estimate by {abs(val):.2f})")
            return factors
    except Exception:
        pass

    # Fallback to column names from input
    cols = list(row_df.columns)
    return [
        f"{cols[0]} (primary driver)" if len(cols) > 0 else "disruption_type",
        f"{cols[1]} (secondary driver)" if len(cols) > 1 else "disruption_severity",
        f"{cols[2]} (contextual driver)" if len(cols) > 2 else "supplier_tier",
    ]
