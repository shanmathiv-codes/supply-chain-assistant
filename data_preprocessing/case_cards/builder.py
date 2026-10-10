"""Case card generator producing standardized, collision-free markdown cards."""
import hashlib
import json
from pathlib import Path

import pandas as pd


def generate_case_narrative(row: dict) -> str:
    """Generate unambiguous 3-sentence narrative avoiding label collisions."""
    severity = row.get("disruption_severity", "Unknown")
    size = row.get("supplier_size", "Unknown")
    d_type = row.get("disruption_type", "disruption")
    industry = row.get("industry", "industry")
    tier = row.get("supplier_tier", "supplier")
    region = row.get("supplier_region", "region")
    backup = "with an existing alternate backup contract" if row.get("has_backup_supplier") else "without a secondary backup supplier"
    impact = row.get("production_impact_pct", 0.0)
    loss = row.get("revenue_loss_usd", 0.0)
    response = row.get("response_type", "standard response")
    rec_days = row.get("full_recovery_days", 0.0)
    switch = "permanently replaced" if row.get("permanent_supplier_change") else "retained without permanent supplier change"

    s1 = (
        f"A {severity.lower()}-severity {d_type.lower()} event occurred in the {industry} sector, "
        f"impacting a {size.lower()}-sized {tier} supplier based in {region} {backup}."
    )
    s2 = (
        f"Initial operations suffered a {impact:.1f}% drop in production capacity with direct financial loss of ${loss:,.2f} USD."
    )
    s3 = (
        f"The operations team initiated '{response}', achieving full operational recovery in {rec_days:.1f} days, "
        f"after which the primary vendor was {switch}."
    )
    return f"{s1} {s2} {s3}"


def format_single_card(row: dict) -> str:
    """Format single row into markdown case card block."""
    cid = row.get("disruption_id", "DIS-UNKNOWN")
    backup_str = "Yes" if row.get("has_backup_supplier") else "No"
    switch_str = "Yes" if row.get("permanent_supplier_change") else "No"

    line1 = (
        f"disruption_id: {cid} | disruption_type: {row.get('disruption_type')} | "
        f"industry: {row.get('industry')} | supplier_tier: {row.get('supplier_tier')} | "
        f"supplier_region: {row.get('supplier_region')} | supplier_size: {row.get('supplier_size')} | "
        f"has_backup_supplier: {backup_str} | disruption_severity: {row.get('disruption_severity')}"
    )
    line2 = (
        f"production_impact_pct: {row.get('production_impact_pct')} | "
        f"revenue_loss_usd: {row.get('revenue_loss_usd')} | "
        f"response_type: {row.get('response_type')} | "
        f"response_time_days: {row.get('response_time_days')} | "
        f"partial_recovery_days: {row.get('partial_recovery_days')} | "
        f"full_recovery_days: {row.get('full_recovery_days')} | "
        f"permanent_supplier_change: {switch_str}"
    )
    narrative = generate_case_narrative(row)

    return f"## Case {cid}\n{line1}\n{line2}\n\n{narrative}\n"


def build_case_cards(
    df: pd.DataFrame,
    target_dir: Path,
    batch_size: int = 100,
) -> tuple[list[Path], Path]:
    """Generate batch markdown files and _index.json tracking sha256 checksums."""
    target_dir.mkdir(parents=True, exist_ok=True)
    batch_files = []
    card_index = {}

    rows = df.to_dict(orient="records")
    for b_idx in range(0, len(rows), batch_size):
        batch_chunk = rows[b_idx : b_idx + batch_size]
        batch_num = (b_idx // batch_size) + 1
        batch_path = target_dir / f"batch_{batch_num:04d}.md"

        card_texts = []
        for r in batch_chunk:
            c_text = format_single_card(r)
            card_texts.append(c_text)
            c_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
            card_index[r["disruption_id"]] = {
                "batch": batch_path.name,
                "sha256": c_hash,
            }

        batch_content = "\n".join(card_texts)
        batch_path.write_text(batch_content, encoding="utf-8")
        batch_files.append(batch_path)

    # Write _index.json
    index_file = target_dir / "_index.json"
    index_file.write_text(json.dumps(card_index, indent=2), encoding="utf-8")

    return batch_files, index_file
