"""End-to-end data pipeline orchestrator for Supply Chain Disruption Assistant."""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from data_preprocessing.case_cards.builder import build_case_cards
from data_preprocessing.case_cards.data_dictionary_builder import build_data_dictionary
from data_preprocessing.case_cards.playbooks import generate_derived_playbooks
from data_preprocessing.data_cleaning.cleaners import (
    normalize_categoricals,
    parse_boolean_series,
    resolve_columns,
)
from data_preprocessing.data_cleaning.quality_report import generate_quality_report
from data_preprocessing.data_cleaning.validators import validate_and_filter_rows
from data_preprocessing.data_storing.manifest import update_manifest
from data_preprocessing.data_storing.parquet_io import save_ledger_parquet
from data_preprocessing.data_storing.sqlite_io import mirror_ledger_to_sqlite
from data_preprocessing.eda.eda import run_signal_check
from data_preprocessing.preprocessing.splitting import create_stratified_splits
from data_preprocessing.preprocessing.synapt_sample import (
    build_synapt_sample_artifacts,
    select_stratified_sample_ids,
)
from data_preprocessing.preprocessing.taxonomy import derive_and_update_taxonomy
from scripts.download_dataset import acquire_dataset


def run_pipeline(source: str = "auto", force_splits: bool = False, sample_size: int = 500) -> dict:
    """Execute complete data pipeline with integrity assertions."""
    t0 = time.time()
    print("=== Supply Chain Disruption Assistant: Data Pipeline ===")

    # Paths
    dataset_dir = ROOT_DIR / "dataset"
    reports_dir = dataset_dir / "reports"
    interim_dir = dataset_dir / "interim"
    processed_dir = dataset_dir / "processed"
    splits_dir = dataset_dir / "splits"
    store_dir = dataset_dir / "store"
    synapt_sample_dir = dataset_dir / "synapt_sample"
    cards_dir = dataset_dir / "case_cards"
    playbooks_dir = dataset_dir / "playbooks"
    schema_doc_dir = dataset_dir / "schema_doc"
    manifest_path = dataset_dir / "MANIFEST.json"

    # Step 1: Acquire
    print("\n[Stage 1/9] Acquiring dataset...")
    raw_path, source_type = acquire_dataset(source=source)
    is_synthetic = source_type == "synthetic"
    df_raw = pd.read_csv(raw_path)
    print(
        f"Loaded raw dataset: {len(df_raw):,} rows, {len(df_raw.columns)} columns from {raw_path}"
    )

    # Step 2: Clean and Normalize
    print("\n[Stage 2/9] Cleaning, resolving columns, and validating schema...")
    df_resolved = resolve_columns(df_raw, reports_dir)
    # Parse booleans
    for b_col in ["has_backup_supplier", "permanent_supplier_change"]:
        if b_col in df_resolved.columns:
            df_resolved[b_col] = parse_boolean_series(df_resolved[b_col])
    # Normalize categoricals
    df_normalized = normalize_categoricals(df_resolved)
    # Validate and filter
    df_clean, df_rejected = validate_and_filter_rows(df_normalized, reports_dir)
    interim_parquet = interim_dir / "cases_clean.parquet"
    interim_dir.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(interim_parquet, index=False)
    print(f"Cleaning complete: {len(df_clean):,} clean cases, {len(df_rejected)} rejected.")

    # Quality Report
    print("Writing data quality reports...")
    generate_quality_report(df_clean, df_rejected, reports_dir, is_synthetic=is_synthetic)

    # Step 3: Store Ledger (Parquet and SQLite)
    print("\n[Stage 3/9] Storing clean ledger and mirroring to SQLite...")
    ledger_parquet = processed_dir / "cases_clean.parquet"
    save_ledger_parquet(df_clean, ledger_parquet)
    sqlite_db = store_dir / "disruptions.db"
    mirror_ledger_to_sqlite(df_clean, sqlite_db)

    # Step 4: Update Taxonomy
    print("\n[Stage 4/9] Deriving canonical taxonomy...")
    derive_and_update_taxonomy(df_clean)

    # Step 5: Stratified Splits
    print("\n[Stage 5/9] Creating stratified train/val/test and calibration splits...")
    splits = create_stratified_splits(df_clean, splits_dir, seed=42, force=force_splits)
    train_df = splits["train"]
    val_df = splits["val"]
    test_df = splits["test"]

    # Step 6: EDA Signal Check
    print("\n[Stage 6/9] Running signal check against median baseline...")
    run_signal_check(train_df, val_df, reports_dir)

    # Step 7: Synapt Stratified Sample
    print(f"\n[Stage 7/9] Building stratified Synapt sample (target size: {sample_size})...")
    sample_ids = select_stratified_sample_ids(train_df, sample_size=sample_size, seed=42)
    build_synapt_sample_artifacts(
        train_df=train_df,
        sample_ids=sample_ids,
        target_dir=synapt_sample_dir,
        reports_dir=reports_dir,
        seed=42,
    )
    # Also write case cards for the sample in dataset/case_cards
    sample_df = train_df[train_df["disruption_id"].isin(sample_ids)].copy()
    build_case_cards(sample_df, cards_dir, batch_size=100)

    # Step 8: Derived Playbooks and Data Dictionary
    print("\n[Stage 8/9] Generating derived playbooks and data dictionary...")
    generate_derived_playbooks(train_df, playbooks_dir, min_cases=5)
    data_dict_path = schema_doc_dir / "data_dictionary.md"
    build_data_dictionary(data_dict_path)

    # Step 9: Integrity Assertions & Manifest
    print("\n[Stage 9/9] Verifying integrity assertions and updating manifest...")
    # Assert disjointness of splits
    train_ids = set(train_df["disruption_id"])
    val_ids = set(val_df["disruption_id"])
    test_ids = set(test_df["disruption_id"])
    assert train_ids.isdisjoint(val_ids), "Integrity failure: Train and Val IDs overlap!"
    assert train_ids.isdisjoint(test_ids), "Integrity failure: Train and Test IDs overlap!"
    assert val_ids.isdisjoint(test_ids), "Integrity failure: Val and Test IDs overlap!"

    # Assert sample is strictly a subset of train
    sample_id_set = set(sample_ids)
    assert sample_id_set.issubset(train_ids), "Integrity failure: Sample contains non-train IDs!"
    assert sample_id_set.isdisjoint(val_ids), "Integrity failure: Sample overlaps with Val split!"
    assert sample_id_set.isdisjoint(test_ids), "Integrity failure: Sample overlaps with Test split!"

    # Update manifest
    manifest_data = update_manifest(
        manifest_path=manifest_path,
        source=source_type,
        raw_path=raw_path,
        clean_path=ledger_parquet,
        row_count=len(df_clean),
        column_list=list(df_clean.columns),
    )

    elapsed = time.time() - t0
    print(f"\nData pipeline finished successfully in {elapsed:.1f}s.")
    print(f"Manifest: {manifest_path} (records={len(df_clean):,}, source={source_type})")
    return manifest_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supply Chain Data Pipeline")
    parser.add_argument("--source", choices=["auto", "real", "synthetic"], default="auto")
    parser.add_argument("--force", action="store_true", help="Force recomputing splits")
    parser.add_argument("--sample-size", type=int, default=500, help="Synapt sample size")
    args = parser.parse_args()
    run_pipeline(source=args.source, force_splits=args.force, sample_size=args.sample_size)
