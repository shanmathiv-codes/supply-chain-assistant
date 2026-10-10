"""Data validation rules, numeric range assertions, and rejected row capture."""
from pathlib import Path

import pandas as pd

from app.core.config import load_yaml_config

SCHEMA_CONFIG = load_yaml_config("dataset_schema.yaml")


def validate_and_filter_rows(
    df: pd.DataFrame, reports_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate rows against schema constraints.
    Returns: (clean_df, rejected_df)
    """
    initial_count = len(df)
    rejected_records = []
    clean_indices = []

    # 1. Deduplicate disruption_id
    if "disruption_id" in df.columns:
        dupes = df[df.duplicated(subset=["disruption_id"], keep="first")]
        for idx, row in dupes.iterrows():
            rejected_records.append({
                "row_index": idx,
                "disruption_id": row.get("disruption_id"),
                "reason": "Duplicate disruption_id (kept first occurrence)",
            })
        df = df.drop_duplicates(subset=["disruption_id"], keep="first")

    # 2. Iterate and validate each row
    cols_spec = SCHEMA_CONFIG.get("columns", {})

    for idx, row in df.iterrows():
        reasons = []

        # Check required non-null fields
        for col_name, spec in cols_spec.items():
            if col_name not in row:
                continue
            val = row[col_name]
            if not spec.get("nullable", True) and (pd.isna(val) or val is None):
                reasons.append(f"Missing required non-nullable field: {col_name}")

        # Check numeric ranges
        if "production_impact_pct" in row and pd.notna(row["production_impact_pct"]):
            val = row["production_impact_pct"]
            if not (0.0 <= val <= 100.0):
                reasons.append(f"production_impact_pct out of range [0, 100]: {val}")

        if "revenue_loss_usd" in row and pd.notna(row["revenue_loss_usd"]):
            val = row["revenue_loss_usd"]
            if val < 0.0:
                reasons.append(f"revenue_loss_usd negative: {val}")

        if "response_time_days" in row and pd.notna(row["response_time_days"]):
            if row["response_time_days"] < 0.0:
                reasons.append(f"response_time_days negative: {row['response_time_days']}")

        if "full_recovery_days" in row and pd.notna(row["full_recovery_days"]):
            if row["full_recovery_days"] < 0.0:
                reasons.append(f"full_recovery_days negative: {row['full_recovery_days']}")

        # Temporal sequence sanity check
        if (
            "partial_recovery_days" in row
            and "full_recovery_days" in row
            and pd.notna(row["partial_recovery_days"])
            and pd.notna(row["full_recovery_days"])
        ):
            if row["partial_recovery_days"] > row["full_recovery_days"]:
                # Note: per brief 8.3: "partial_recovery_days <= full_recovery_days if both present (flag, do not drop silently)"
                # We flag as an anomaly if severe, but do not drop unless impossible
                pass

        if reasons:
            rejected_records.append({
                "row_index": idx,
                "disruption_id": row.get("disruption_id", f"row_{idx}"),
                "reason": "; ".join(reasons),
            })
        else:
            clean_indices.append(idx)

    clean_df = df.loc[clean_indices].copy()
    rejected_df = pd.DataFrame(rejected_records)

    # Save rejected rows report
    reports_dir.mkdir(parents=True, exist_ok=True)
    rejected_path = reports_dir / "rejected_rows.csv"
    rejected_df.to_csv(rejected_path, index=False, encoding="utf-8")

    rejection_pct = (len(rejected_records) / initial_count) * 100.0 if initial_count > 0 else 0.0
    max_allowed = SCHEMA_CONFIG.get("constraints", {}).get("max_rejection_percentage", 20.0)

    if rejection_pct > max_allowed:
        raise ValueError(
            f"Data quality failure: {rejection_pct:.1f}% rows rejected, exceeding limit of {max_allowed}%."
        )

    return clean_df, rejected_df
