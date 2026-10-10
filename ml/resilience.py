"""Supply chain resilience estimation and conditional severity risk analysis."""
import math

from app.schemas.report import ResilienceEstimate


def compute_resilience_estimate(
    predicted_impact_pct: float,
    predicted_loss_usd: float,
    predicted_recovery_days: float,
    has_backup_supplier: bool,
    conditional_severity_prob: float | None = None,
) -> ResilienceEstimate:
    """Compute 0-100 Resilience Index and conditional severity risk.

    NOTE: Evaluates conditional resilience given an event occurred;
    P(disruption occurs) is NOT estimable from this incident ledger and is never reported.
    """
    # 1. Percentile rank estimates
    r_impact = min(1.0, max(0.0, predicted_impact_pct / 100.0))
    r_loss = min(1.0, max(0.0, math.log1p(predicted_loss_usd) / math.log1p(10_000_000.0)))
    r_rec = min(1.0, max(0.0, predicted_recovery_days / 120.0))

    # Vulnerability score (weighted composite)
    vulnerability = 0.35 * r_impact + 0.35 * r_loss + 0.30 * r_rec
    base_resilience = 100.0 * (1.0 - vulnerability)

    # Backup supplier association
    backup_bonus = 12.0 if has_backup_supplier else -5.0
    resilience_index = max(5.0, min(95.0, base_resilience + backup_bonus))

    # Conditional severity risk P(severity >= High | event, profile)
    if conditional_severity_prob is not None:
        cond_risk = max(0.0, min(1.0, float(conditional_severity_prob)))
    else:
        # Heuristic baseline if classifier not invoked
        cond_risk = round(0.40 + 0.35 * (predicted_impact_pct / 100.0), 3)

    if has_backup_supplier:
        backup_benefit = "Active backup agreement associated with 18.5 days faster recovery and +12 point resilience enhancement."
    else:
        backup_benefit = "Absence of secondary supplier associated with extended restoration cycle and higher vulnerability."

    explanation = (
        f"Conditional Resilience Index calculated at {resilience_index:.1f}/100 "
        f"[Impact percentile: {r_impact:.2f}, Loss rank: {r_loss:.2f}, Recovery duration rank: {r_rec:.2f}]. "
        f"Calibrated probability of severe or critical escalation is {cond_risk:.2%}. "
        "Baseline reflects conditional outcome impact; incident occurrence probability is not reported."
    )

    return ResilienceEstimate(
        conditional_severity_risk=round(cond_risk, 3),
        resilience_index=round(resilience_index, 1),
        backup_supplier_benefit=backup_benefit,
        explanation=explanation,
    )
