"""Stratified Synapt sample builder: sample selection, card/csv batches, pilot, and checklist."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from data_preprocessing.case_cards.builder import build_case_cards, format_single_card


def select_stratified_sample_ids(
    train_df: pd.DataFrame,
    sample_size: int = 500,
    seed: int = 42,
    min_per_value: int = 5,
) -> list[str]:
    """Select stratified sample of train IDs ensuring categorical coverage."""
    if len(train_df) <= sample_size:
        return list(train_df["disruption_id"].astype(str))

    selected_indices = set()
    cat_columns = [
        "disruption_type",
        "industry",
        "supplier_tier",
        "supplier_region",
        "supplier_size",
        "has_backup_supplier",
        "disruption_severity",
        "response_type",
    ]

    # 1. Guarantee coverage across each categorical value
    rng = train_df.sample(frac=1.0, random_state=seed)
    for col in cat_columns:
        for val, group in rng.groupby(col):
            take_n = min(len(group), min_per_value)
            for idx in group.index[:take_n]:
                selected_indices.add(idx)

    # 2. Fill remainder proportionally to (disruption_type, disruption_severity)
    remaining_needed = sample_size - len(selected_indices)
    if remaining_needed > 0:
        remaining_df = train_df.drop(index=list(selected_indices))
        strata = (
            remaining_df["disruption_type"].astype(str)
            + "___"
            + remaining_df["disruption_severity"].astype(str)
        )
        # Sample proportionally
        proportional_sample = remaining_df.groupby(strata, group_keys=False).apply(
            lambda grp: grp.sample(
                n=max(1, int(round(len(grp) / len(remaining_df) * remaining_needed))),
                random_state=seed,
            )
        )
        for idx in proportional_sample.index:
            if len(selected_indices) >= sample_size:
                break
            selected_indices.add(idx)

    # If still slightly under/over due to rounding
    if len(selected_indices) < sample_size:
        leftover = train_df.drop(index=list(selected_indices))
        for idx in leftover.index[: sample_size - len(selected_indices)]:
            selected_indices.add(idx)

    chosen_df = train_df.loc[list(selected_indices)[:sample_size]]
    return list(chosen_df["disruption_id"].astype(str))


def build_synapt_sample_artifacts(
    train_df: pd.DataFrame,
    sample_ids: list[str],
    target_dir: Path,
    reports_dir: Path,
    seed: int = 42,
    sample_format: str = "cards",
) -> dict:
    """Build all Synapt sample files: cards, csv, pilot, checklist, and representativeness report."""
    target_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    sample_df = train_df[train_df["disruption_id"].isin(sample_ids)].copy()

    # 1. Write sample_ids.json and pilot_ids.json (first 50)
    (target_dir / "sample_ids.json").write_text(json.dumps(sample_ids, indent=2), encoding="utf-8")
    pilot_ids = sample_ids[:50]
    (target_dir / "pilot_ids.json").write_text(json.dumps(pilot_ids, indent=2), encoding="utf-8")

    # 2. Write Pilot folder: both cards and csv for the same 50 IDs
    pilot_dir = target_dir / "pilot"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    pilot_df = train_df[train_df["disruption_id"].isin(pilot_ids)].copy()
    pilot_df.to_csv(pilot_dir / "pilot_50.csv", index=False, encoding="utf-8")

    pilot_cards = [format_single_card(r) for r in pilot_df.to_dict(orient="records")]
    (pilot_dir / "pilot_50_cards.md").write_text("\n".join(pilot_cards), encoding="utf-8")

    # 3. Write sample batches in chosen format(s)
    cards_dir = target_dir / "cards"
    csv_dir = target_dir / "csv"
    build_case_cards(sample_df, cards_dir, batch_size=100)

    # Also write CSV batches (500 rows per file)
    csv_dir.mkdir(parents=True, exist_ok=True)
    for b_idx in range(0, len(sample_df), 500):
        b_df = sample_df.iloc[b_idx : b_idx + 500]
        b_num = (b_idx // 500) + 1
        b_df.to_csv(csv_dir / f"batch_{b_num:04d}.csv", index=False, encoding="utf-8")

    # 4. Ingest checklist markdown
    checklist_lines = [
        "# Synapt Ingestion Checklist",
        "",
        f"- Target Sample Size: {len(sample_ids)}",
        f"- Pilot Set: `pilot/pilot_50_cards.md` and `pilot/pilot_50.csv` ({len(pilot_ids)} cases)",
        "",
        "## Pilot Ingestion",
        "- [ ] Step 1: Ingest `pilot/pilot_50_cards.md` into trial provider",
        "- [ ] Step 2: Audit Context Graph for edge types and collision-free attribute nodes",
        "",
        "## Sample Batch Uploads",
    ]
    batch_card_files = sorted(list(cards_dir.glob("batch_*.md")))
    for bf in batch_card_files:
        h = hashlib.sha256(bf.read_bytes()).hexdigest()[:12]
        checklist_lines.append(f"- [ ] `{bf.name}` (sha256: `{h}...`)")

    (target_dir / "ingest_checklist.md").write_text("\n".join(checklist_lines), encoding="utf-8")

    # 5. Representativeness report
    rep_lines = [
        "# Sample Representativeness Report",
        "",
        f"- Full Training Population: {len(train_df):,} records",
        f"- Synapt Sample Size: {len(sample_df):,} records",
        "",
        "## Numeric Outcome Comparison (Median)",
        "| Metric | Full Train Median | Sample Median | Absolute Difference |",
        "|---|---|---|---|",
    ]
    for col in ["production_impact_pct", "revenue_loss_usd", "full_recovery_days"]:
        tr_med = float(train_df[col].median())
        sp_med = float(sample_df[col].median())
        diff = abs(tr_med - sp_med)
        rep_lines.append(f"| `{col}` | {tr_med:,.1f} | {sp_med:,.1f} | {diff:,.1f} |")

    (reports_dir / "sample_representativeness.md").write_text(
        "\n".join(rep_lines), encoding="utf-8"
    )

    return {
        "sample_size": len(sample_ids),
        "pilot_size": len(pilot_ids),
        "cards_batches": len(batch_card_files),
    }
