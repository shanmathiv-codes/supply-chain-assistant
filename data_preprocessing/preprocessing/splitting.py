"""Dataset splitting: 80/10/10 stratified train/val/test and 20% calibration slice."""

import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


def create_stratified_splits(
    df: pd.DataFrame,
    splits_dir: Path,
    seed: int = 42,
    force: bool = False,
) -> dict[str, pd.DataFrame]:
    """Create or load deterministic train, val, test, and calibration splits."""
    splits_dir.mkdir(parents=True, exist_ok=True)
    id_files = {
        "train": splits_dir / "train_ids.json",
        "val": splits_dir / "val_ids.json",
        "test": splits_dir / "test_ids.json",
        "calibration": splits_dir / "calibration_ids.json",
    }

    # If ID files exist and force=False, load existing splits
    if not force and all(f.exists() for f in id_files.values()):
        print("Using existing split IDs...")
        loaded = {}
        for split_name, fpath in id_files.items():
            ids = json.loads(fpath.read_text(encoding="utf-8"))
            split_df = df[df["disruption_id"].isin(ids)].copy()
            loaded[split_name] = split_df
        return loaded

    print(f"Computing new stratified splits (80/10/10) with seed={seed}...")

    # Create composite stratification stratum
    strata = df["disruption_type"].astype(str) + "___" + df["disruption_severity"].astype(str)
    counts = strata.value_counts()
    rare_strata = counts[counts < 3].index
    strata_clean = strata.apply(lambda s: "other" if s in rare_strata else s)

    # 1. Split Train (80%) vs Temp (20%)
    train_df, temp_df, _, temp_strata = train_test_split(
        df,
        strata_clean,
        test_size=0.20,
        random_state=seed,
        stratify=strata_clean,
    )

    # 2. Split Temp (20%) into Val (10%) and Test (10%)
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=seed,
        stratify=temp_strata,
    )

    # 3. Carve Calibration slice (20% of Train)
    train_strata = (
        train_df["disruption_type"].astype(str)
        + "___"
        + train_df["disruption_severity"].astype(str)
    )
    train_counts = train_strata.value_counts()
    train_rare = train_counts[train_counts < 3].index
    train_strata_clean = train_strata.apply(lambda s: "other" if s in train_rare else s)

    _, cal_df = train_test_split(
        train_df,
        test_size=0.20,
        random_state=seed,
        stratify=train_strata_clean,
    )

    splits = {
        "train": train_df,
        "val": val_df,
        "test": test_df,
        "calibration": cal_df,
    }

    # Save IDs and parquet
    for split_name, split_df in splits.items():
        ids = list(split_df["disruption_id"].astype(str))
        id_files[split_name].write_text(json.dumps(ids, indent=2), encoding="utf-8")
        split_df.to_parquet(splits_dir / f"{split_name}.parquet", index=False)

    print(
        f"Splits saved: Train={len(train_df):,}, Val={len(val_df):,}, "
        f"Test={len(test_df):,}, Calibration={len(cal_df):,}"
    )
    return splits
