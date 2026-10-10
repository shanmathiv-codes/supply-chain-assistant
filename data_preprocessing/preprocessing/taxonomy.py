"""Derive canonical categorical values from clean ledger and update taxonomy.yaml."""

from pathlib import Path

import pandas as pd
import yaml

from app.core.config import load_yaml_config

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def derive_and_update_taxonomy(df: pd.DataFrame) -> dict:
    """Derive observed categories, preserve existing synonyms, and save config/taxonomy.yaml."""
    current_taxonomy = load_yaml_config("taxonomy.yaml")
    cat_columns = [
        "disruption_type",
        "industry",
        "supplier_tier",
        "supplier_region",
        "supplier_size",
        "disruption_severity",
        "response_type",
    ]

    updated = {}
    for col in cat_columns:
        if col in df.columns:
            observed = sorted([str(x) for x in df[col].dropna().unique() if str(x).strip()])
            existing_spec = current_taxonomy.get(col, {})
            existing_allowed = existing_spec.get("allowed_values", [])
            # Union while preserving deterministic order
            combined_allowed = sorted(list(set(existing_allowed).union(set(observed))))
            synonyms = existing_spec.get("synonyms", {})
            updated[col] = {
                "allowed_values": combined_allowed,
                "synonyms": synonyms,
            }
        elif col in current_taxonomy:
            updated[col] = current_taxonomy[col]

    tax_file = CONFIG_DIR / "taxonomy.yaml"
    with open(tax_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(updated, f, sort_keys=False)

    return updated
