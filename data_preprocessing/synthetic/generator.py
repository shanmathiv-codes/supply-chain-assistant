"""Schema-faithful synthetic data generator for Supply Chain Disruption dataset.

Generating rules:
1. disruption_severity (Low, Medium, High, Critical) drives baseline production_impact_pct and revenue_loss_usd.
2. Lack of backup supplier (has_backup_supplier=False) adds penalty to production impact, revenue loss, and recovery times.
3. revenue_loss_usd is drawn from log-normal distribution scaled by severity and supplier size.
4. response_time_days <= partial_recovery_days <= full_recovery_days.
5. permanent_supplier_change is more probable for Critical/High severity events without backup suppliers.
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

DISRUPTION_TYPES = [
    "Natural Disaster",
    "Supplier Bankruptcy",
    "Operational Failure",
    "Labor Strike",
    "Transportation Delay",
    "Cyber Incident",
    "Quality Issue",
    "Geopolitical",
]

INDUSTRIES = [
    "Automotive",
    "Electronics",
    "Pharmaceuticals",
    "Aerospace",
    "Consumer Goods",
    "Energy",
    "Chemicals",
    "Industrial",
]

SUPPLIER_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
SUPPLIER_REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East & Africa"]
SUPPLIER_SIZES = ["Small", "Medium", "Large"]
SEVERITIES = ["Low", "Medium", "High", "Critical"]
RESPONSE_TYPES = [
    "Reroute Shipments",
    "Activate Backup Supplier",
    "Expedite Freight",
    "Buffer Inventory",
    "Production Rescheduling",
    "Renegotiate Contract",
    "Accept Delay",
]

SEVERITY_IMPACT_BASE = {"Low": 12.0, "Medium": 28.0, "High": 55.0, "Critical": 80.0}
SEVERITY_LOSS_SCALE = {"Low": 10.0, "Medium": 11.5, "High": 13.0, "Critical": 14.5}
SEVERITY_RECOVERY_BASE = {"Low": 14.0, "Medium": 35.0, "High": 75.0, "Critical": 140.0}


def generate_synthetic_dataset(n_rows: int = 3000, seed: int = 42) -> pd.DataFrame:
    """Generate n_rows of synthetic disruption records with realistic correlations."""
    np.random.seed(seed)
    random.seed(seed)

    rows = []
    for i in range(1, n_rows + 1):
        case_id = f"DIS-{i:05d}"
        d_type = random.choice(DISRUPTION_TYPES)
        ind = random.choice(INDUSTRIES)
        tier = random.choices(SUPPLIER_TIERS, weights=[0.45, 0.35, 0.20])[0]
        region = random.choice(SUPPLIER_REGIONS)
        size = random.choices(SUPPLIER_SIZES, weights=[0.30, 0.50, 0.20])[0]
        has_backup = random.choice([True, False])
        severity = random.choices(SEVERITIES, weights=[0.25, 0.40, 0.25, 0.10])[0]

        # Calculate production impact %
        base_imp = SEVERITY_IMPACT_BASE[severity]
        backup_factor = 0.75 if has_backup else 1.25
        size_factor = 1.1 if size == "Large" else (1.0 if size == "Medium" else 0.9)
        imp_noise = np.random.normal(0, 5.0)
        prod_impact = float(np.clip(base_imp * backup_factor * size_factor + imp_noise, 1.0, 99.0))

        # Revenue loss USD (log-normal)
        loss_mu = SEVERITY_LOSS_SCALE[severity] + (0.3 if not has_backup else -0.2) + (0.4 if size == "Large" else 0.0)
        loss_usd = float(np.random.lognormal(mean=loss_mu, sigma=0.6))
        loss_usd = max(1000.0, round(loss_usd, 2))

        # Response type and timeline
        resp_type = random.choice(RESPONSE_TYPES)
        resp_days = float(np.clip(np.random.exponential(scale=4.0) + 1.0, 1.0, 60.0))
        resp_days = round(resp_days, 1)

        base_rec = SEVERITY_RECOVERY_BASE[severity]
        full_rec = float(np.clip(base_rec * backup_factor + np.random.normal(0, base_rec * 0.2), resp_days + 5.0, 720.0))
        full_rec = round(full_rec, 1)

        partial_rec = float(np.clip(resp_days + (full_rec - resp_days) * np.random.uniform(0.3, 0.7), resp_days, full_rec))
        partial_rec = round(partial_rec, 1)

        # Permanent supplier change probability
        switch_prob = 0.05
        if severity in ("High", "Critical"):
            switch_prob += 0.20
        if not has_backup:
            switch_prob += 0.15
        if size == "Small":
            switch_prob += 0.10
        perm_change = bool(random.random() < min(0.75, switch_prob))

        rows.append({
            "disruption_id": case_id,
            "disruption_type": d_type,
            "industry": ind,
            "supplier_tier": tier,
            "supplier_region": region,
            "supplier_size": size,
            "has_backup_supplier": has_backup,
            "disruption_severity": severity,
            "production_impact_pct": round(prod_impact, 2),
            "revenue_loss_usd": loss_usd,
            "response_type": resp_type,
            "response_time_days": resp_days,
            "partial_recovery_days": partial_rec,
            "full_recovery_days": full_rec,
            "permanent_supplier_change": perm_change,
        })

    df = pd.DataFrame(rows)
    return df


def save_synthetic_csv(target_path: Path, n_rows: int = 3000, seed: int = 42) -> Path:
    """Generate and write synthetic CSV with disclaimer header."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_dataset(n_rows=n_rows, seed=seed)
    df.to_csv(target_path, index=False, encoding="utf-8")
    return target_path
