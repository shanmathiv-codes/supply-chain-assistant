"""Generate comprehensive data quality JSON and Markdown reports."""
import json
from pathlib import Path

import pandas as pd


def generate_quality_report(
    clean_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    reports_dir: Path,
    is_synthetic: bool = False,
) -> dict:
    """Compute data quality statistics and export report documents."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    total_rows = len(clean_df) + len(rejected_df)
    missing_rates = {col: float(clean_df[col].isna().mean()) for col in clean_df.columns}

    # Category counts
    cat_cols = [
        "disruption_type",
        "industry",
        "supplier_tier",
        "supplier_region",
        "supplier_size",
        "disruption_severity",
        "response_type",
    ]
    category_counts = {}
    for col in cat_cols:
        if col in clean_df.columns:
            category_counts[col] = {str(k): int(v) for k, v in clean_df[col].value_counts().items()}

    # Numeric summary & skew
    num_cols = ["production_impact_pct", "revenue_loss_usd", "response_time_days", "full_recovery_days"]
    numeric_stats = {}
    for col in num_cols:
        if col in clean_df.columns:
            s = clean_df[col].dropna()
            numeric_stats[col] = {
                "min": float(s.min()),
                "max": float(s.max()),
                "mean": float(s.mean()),
                "median": float(s.median()),
                "std": float(s.std()),
                "skew": float(s.skew()) if len(s) > 2 else 0.0,
            }

    report_data = {
        "is_synthetic": is_synthetic,
        "total_rows_inspected": total_rows,
        "clean_rows": len(clean_df),
        "rejected_rows": len(rejected_df),
        "rejection_percentage": round((len(rejected_df) / total_rows) * 100.0, 2) if total_rows > 0 else 0.0,
        "missing_rates": missing_rates,
        "numeric_stats": numeric_stats,
        "category_counts": category_counts,
    }

    # Write JSON
    (reports_dir / "data_quality.json").write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # Write Markdown
    md_lines = [
        "# Data Quality Report",
        "",
    ]
    if is_synthetic:
        md_lines.extend([
            "> [!WARNING]",
            "> **SYNTHETIC DATA DISCLAIMER**: This dataset was synthetically generated. Outcomes, relationships, and metrics must not be interpreted as real-world supply chain observations.",
            "",
        ])

    md_lines.extend([
        f"- **Clean Records:** {len(clean_df):,}",
        f"- **Rejected Records:** {len(rejected_df):,}",
        f"- **Rejection Rate:** {report_data['rejection_percentage']}%",
        "",
        "## Numeric Distributions and Skewness",
        "| Metric | Min | Median | Mean | Max | Skew |",
        "|---|---|---|---|---|---|",
    ])
    for col, st in numeric_stats.items():
        md_lines.append(
            f"| `{col}` | {st['min']:,.1f} | {st['median']:,.1f} | {st['mean']:,.1f} | {st['max']:,.1f} | {st['skew']:.2f} |"
        )

    md_lines.extend([
        "",
        "## Categorical Value Counts",
    ])
    for col, counts in category_counts.items():
        md_lines.append(f"### {col}")
        for val, count in counts.items():
            md_lines.append(f"- **{val}**: {count:,}")
        md_lines.append("")

    (reports_dir / "data_quality.md").write_text("\n".join(md_lines), encoding="utf-8")
    return report_data
