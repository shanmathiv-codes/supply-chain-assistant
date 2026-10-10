"""Data cleaning functions, column normalization, and type coercion."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import load_yaml_config

SCHEMA_CONFIG = load_yaml_config("dataset_schema.yaml")
TAXONOMY_CONFIG = load_yaml_config("taxonomy.yaml")


def resolve_columns(df: pd.DataFrame, reports_dir: Path) -> pd.DataFrame:
    """Map raw dataframe columns to canonical names using dataset_schema.yaml aliases."""
    expected_cols = SCHEMA_CONFIG.get("columns", {})
    mapping = {}
    unresolved = []

    raw_cols = list(df.columns)
    normalized_raw = {c.lower().replace(" ", "_"): c for c in raw_cols}

    for canonical_name, spec in expected_cols.items():
        # 1. Exact match
        if canonical_name in raw_cols:
            mapping[canonical_name] = canonical_name
            continue

        # 2. Case and underscore insensitive match
        norm_key = canonical_name.lower().replace(" ", "_")
        if norm_key in normalized_raw:
            mapping[normalized_raw[norm_key]] = canonical_name
            continue

        # 3. Aliases check
        matched = False
        aliases = spec.get("aliases", [])
        for alias in aliases:
            norm_alias = alias.lower().replace(" ", "_")
            if norm_alias in normalized_raw:
                mapping[normalized_raw[norm_alias]] = canonical_name
                matched = True
                break

        if not matched and spec.get("required", False):
            unresolved.append(canonical_name)

    # Save mapping report
    reports_dir.mkdir(parents=True, exist_ok=True)
    mapping_file = reports_dir / "column_mapping.json"
    mapping_file.write_text(json.dumps(mapping, indent=2), encoding="utf-8")

    if unresolved:
        raise ValueError(
            f"Required dataset columns unresolved in input: {unresolved}. "
            f"Available columns: {raw_cols}"
        )

    # Rename dataframe
    return df.rename(columns=mapping)


def parse_boolean_series(series: pd.Series) -> pd.Series:
    """Safely coerce series to boolean values."""

    def _parse_val(val: Any) -> bool | None:
        if pd.isna(val):
            return None
        if isinstance(val, (bool, np.bool_)):
            return bool(val)
        s = str(val).strip().lower()
        if s in ("1", "true", "yes", "y", "t"):
            return True
        if s in ("0", "false", "no", "n", "f"):
            return False
        return None

    import numpy as np

    return series.apply(_parse_val)


def normalize_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Trim strings and map categoricals via taxonomy synonyms."""
    for col, spec in TAXONOMY_CONFIG.items():
        if col in df.columns:
            synonyms = spec.get("synonyms", {})
            allowed = spec.get("allowed_values", [])
            allowed_lower = {v.lower(): v for v in allowed}

            def _clean_cat(val: Any) -> str | None:
                if pd.isna(val):
                    return None
                s = str(val).strip()
                s_lower = s.lower()
                if s_lower in synonyms:
                    return synonyms[s_lower]
                if s_lower in allowed_lower:
                    return allowed_lower[s_lower]
                return s

            df[col] = df[col].apply(_clean_cat)
    return df
