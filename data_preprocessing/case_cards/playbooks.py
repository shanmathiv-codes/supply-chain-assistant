"""Derived operational playbooks (SOPs) synthesized from full training dataset."""
from pathlib import Path

import pandas as pd


def generate_derived_playbooks(
    train_df: pd.DataFrame,
    playbooks_dir: Path,
    min_cases: int = 5,
) -> list[Path]:
    """Generate derived markdown SOP per disruption type from training observations."""
    playbooks_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    types = train_df["disruption_type"].dropna().unique()
    for d_type in sorted(types):
        sub_df = train_df[train_df["disruption_type"] == d_type]
        n_cases = len(sub_df)
        if n_cases < min_cases:
            continue

        filename = d_type.lower().replace(" ", "_").replace("&", "and") + ".md"
        out_path = playbooks_dir / filename

        # Compute Step 2: response options breakdown
        resp_lines = []
        for r_type, grp in sub_df.groupby("response_type"):
            n_r = len(grp)
            med_rec = grp["full_recovery_days"].median()
            min_rec = grp["full_recovery_days"].min()
            max_rec = grp["full_recovery_days"].max()
            resp_lines.append(
                f"- **{r_type}** (n={n_r} cases, median full recovery {med_rec:.1f} days, range {min_rec:.1f}-{max_rec:.1f} days)"
            )

        # Compute Step 3 milestones
        resp_time_med = sub_df["response_time_days"].median()
        part_rec_med = sub_df["partial_recovery_days"].median()
        full_rec_med = sub_df["full_recovery_days"].median()

        # Compute Step 4 supplier change %
        switch_pct = (sub_df["permanent_supplier_change"].mean()) * 100.0

        content = f"""[DERIVED]
# Playbook: {d_type} (derived from {n_cases:,} historical cases)
*Computed from full training data (n={n_cases:,}), not solely the Synapt sample.*

**Intent:** Guide tactical mitigation and operational recovery milestones for {d_type} disruptions.

## Step 1 - Confirm profile and severity
- Prerequisites: Verify supplier tier, region, operating scale, disruption severity, and backup contract status.
- Baseline check: Confirm whether primary vendor has immediate secondary sourcing options enabled.

## Step 2 - Consider response options seen historically
{chr(10).join(resp_lines)}

## Step 3 - Monitor operational recovery milestones
- Typical response initiation: {resp_time_med:.1f} days
- Median partial operational recovery: {part_rec_med:.1f} days
- Median full operational recovery: {full_rec_med:.1f} days

## Step 4 - Assess supplier change probability
- A permanent supplier replacement followed in {switch_pct:.1f}% of historical {d_type} cases.
- Evaluate whether root cause or supplier bankruptcy warrants long-term vendor contract renegotiation.

**Caveats:** Associations only. Statistical summaries computed over observed historical data; not an official corporate standard operating procedure.
"""
        out_path.write_text(content.strip() + "\n", encoding="utf-8")
        generated_files.append(out_path)

    return generated_files
