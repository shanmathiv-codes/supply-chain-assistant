"""Split-conformal prediction interval calculation and coverage evaluation."""
import math

import numpy as np


class SplitConformalPredictor:
    """Computes exact split-conformal prediction intervals with distribution-free nominal coverage."""

    def __init__(self, nominal_coverage: float = 0.80):
        self.nominal_coverage = nominal_coverage
        self.q_val: float | None = None

    def calibrate(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calibrate non-conformity threshold on held-out calibration set.
        q = (1 - alpha) * (1 + 1/n) empirical quantile of absolute residuals.
        """
        residuals = np.abs(np.array(y_true) - np.array(y_pred))
        n = len(residuals)
        if n == 0:
            self.q_val = 0.0
            return 0.0

        p = min(1.0, math.ceil((n + 1) * self.nominal_coverage) / n)
        # Empirical quantile with linear interpolation
        self.q_val = float(np.quantile(residuals, p, method="higher"))
        return self.q_val

    def predict_interval(
        self,
        point_preds: np.ndarray | float,
        clip_min: float | None = 0.0,
        clip_max: float | None = None,
    ) -> tuple[np.ndarray | float, np.ndarray | float]:
        """Produce [low, high] interval centered at point prediction."""
        q = self.q_val if self.q_val is not None else 0.0
        pts = np.array(point_preds)
        low = pts - q
        high = pts + q

        if clip_min is not None:
            low = np.maximum(low, clip_min)
            high = np.maximum(high, clip_min)
        if clip_max is not None:
            low = np.minimum(low, clip_max)
            high = np.minimum(high, clip_max)

        if np.ndim(point_preds) == 0:
            return float(low), float(high)
        return low, high

    def evaluate_coverage(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
        """Compute empirical coverage and mean interval width on evaluation data."""
        low, high = self.predict_interval(y_pred)
        y = np.array(y_true)
        covered = (y >= low) & (y <= high)
        coverage = float(np.mean(covered))
        mean_width = float(np.mean(high - low))
        return {
            "nominal_coverage": self.nominal_coverage,
            "empirical_coverage": round(coverage, 4),
            "mean_interval_width": round(mean_width, 2),
            "q_val": round(self.q_val or 0.0, 2),
        }
