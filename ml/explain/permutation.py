"""Permutation feature importance fallback module."""
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def compute_permutation_factors(
    pipeline: Any,
    X_sample: pd.DataFrame,
    y_sample: pd.Series,
    top_n: int = 3,
) -> list[str]:
    """Calculate top predictive factors using permutation importance on validation sample."""
    try:
        r = permutation_importance(
            pipeline,
            X_sample,
            y_sample,
            n_repeats=3,
            random_state=42,
            n_jobs=1,
        )
        importances = r.importances_mean
        feature_names = list(X_sample.columns)
        sorted_idx = np.argsort(importances)[::-1]
        top_factors = []
        for idx in sorted_idx[:top_n]:
            feat = feature_names[idx]
            imp = importances[idx]
            top_factors.append(f"{feat} (importance: {imp:.3f})")
        return top_factors
    except Exception:
        return [f"{col} (standard factor)" for col in list(X_sample.columns)[:top_n]]
