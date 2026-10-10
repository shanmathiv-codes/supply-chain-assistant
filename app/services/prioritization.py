"""Disruption prioritization service computing triage score P1-P4 and sensitivity analysis."""

import math

from app.core.config import load_yaml_config
from app.schemas.report import PriorityAssessment

PRIORITY_CONFIG = load_yaml_config("priority.yaml")
WEIGHTS = PRIORITY_CONFIG.get(
    "weights", {"severity": 0.40, "production_impact": 0.35, "financial_loss": 0.25}
)
SEVERITY_MAP = PRIORITY_CONFIG.get(
    "severity_map", {"Low": 0.10, "Medium": 0.40, "High": 0.75, "Critical": 1.00}
)
BANDS = PRIORITY_CONFIG.get("bands", {})
DELTA = PRIORITY_CONFIG.get("sensitivity", {}).get("delta", 0.10)


class PrioritizationService:
    """Computes formula-grounded priority scores (0-100), operational triage bands, and sensitivity."""

    def _determine_band(self, score: float) -> tuple[str, str, str]:
        if score >= BANDS.get("P1", {}).get("min_score", 75.0):
            return (
                "P1",
                BANDS.get("P1", {}).get("label", "Critical Escalation"),
                BANDS.get("P1", {}).get("description", ""),
            )
        if score >= BANDS.get("P2", {}).get("min_score", 55.0):
            return (
                "P2",
                BANDS.get("P2", {}).get("label", "High Priority"),
                BANDS.get("P2", {}).get("description", ""),
            )
        if score >= BANDS.get("P3", {}).get("min_score", 35.0):
            return (
                "P3",
                BANDS.get("P3", {}).get("label", "Medium Priority"),
                BANDS.get("P3", {}).get("description", ""),
            )
        return (
            "P4",
            BANDS.get("P4", {}).get("label", "Low Priority"),
            BANDS.get("P4", {}).get("description", ""),
        )

    def calculate_priority(
        self,
        severity: str | None,
        production_impact_pct: float | None = None,
        revenue_loss_usd: float | None = None,
        predicted_impact_pct: float | None = None,
        predicted_loss_usd: float | None = None,
    ) -> PriorityAssessment:
        based_on_predictions = False

        # 1. Severity component S in [0, 1]
        sev_norm = (severity or "Medium").capitalize()
        s_val = SEVERITY_MAP.get(sev_norm, 0.40)

        # 2. Impact component I in [0, 1]
        if production_impact_pct is not None:
            imp_val = min(100.0, max(0.0, float(production_impact_pct))) / 100.0
        elif predicted_impact_pct is not None:
            imp_val = min(100.0, max(0.0, float(predicted_impact_pct))) / 100.0
            based_on_predictions = True
        else:
            imp_val = 0.35  # default baseline moderate impact

        # 3. Financial loss percentile F in [0, 1]
        loss = revenue_loss_usd if revenue_loss_usd is not None else predicted_loss_usd
        if revenue_loss_usd is None and predicted_loss_usd is not None:
            based_on_predictions = True

        if loss is not None and loss > 0:
            # log1p transformation scaled against 10M ceiling
            log_loss = math.log1p(float(loss))
            loss_val = min(1.0, max(0.0, log_loss / math.log1p(10_000_000.0)))
        else:
            loss_val = 0.25

        w_s = WEIGHTS.get("severity", 0.40)
        w_p = WEIGHTS.get("production_impact", 0.35)
        w_f = WEIGHTS.get("financial_loss", 0.25)

        score = round(100.0 * (w_s * s_val + w_p * imp_val + w_f * loss_val), 1)
        band, band_label, band_desc = self._determine_band(score)

        # Sensitivity analysis (+/- delta perturbation on weights)
        sensitivity = {
            "severity_plus_10": round(
                100.0
                * (
                    (w_s + DELTA) * s_val
                    + (w_p - DELTA / 2) * imp_val
                    + (w_f - DELTA / 2) * loss_val
                ),
                1,
            ),
            "severity_minus_10": round(
                100.0
                * (
                    (w_s - DELTA) * s_val
                    + (w_p + DELTA / 2) * imp_val
                    + (w_f + DELTA / 2) * loss_val
                ),
                1,
            ),
            "impact_plus_10": round(
                100.0
                * (
                    (w_s - DELTA / 2) * s_val
                    + (w_p + DELTA) * imp_val
                    + (w_f - DELTA / 2) * loss_val
                ),
                1,
            ),
            "loss_plus_10": round(
                100.0
                * (
                    (w_s - DELTA / 2) * s_val
                    + (w_p - DELTA / 2) * imp_val
                    + (w_f + DELTA) * loss_val
                ),
                1,
            ),
        }

        source_note = "predicted values" if based_on_predictions else "observed event data"
        reason = (
            f"Assigned triage band {band} ({band_label}) with priority score {score}/100 based on {source_note} "
            f"[Severity: {sev_norm} ({s_val:.2f}), Production Impact: {imp_val * 100:.1f}%, Financial Loss Score: {loss_val:.2f}]. {band_desc}"
        )

        return PriorityAssessment(
            score=score,
            band=band,
            band_label=band_label,
            components={
                "severity_score": round(s_val * 100, 1),
                "impact_score": round(imp_val * 100, 1),
                "financial_score": round(loss_val * 100, 1),
            },
            reason=reason,
            sensitivity=sensitivity,
            based_on_predicted_values=based_on_predictions,
        )


prioritization_service = PrioritizationService()
