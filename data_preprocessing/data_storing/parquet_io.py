"""Parquet I/O operations using pyarrow with snappy compression and schema metadata."""

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def save_ledger_parquet(df: pd.DataFrame, target_path: Path) -> Path:
    """Save cleaned cases as indexed Parquet ledger and export schema.json."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to PyArrow table
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, target_path, compression="snappy")

    # Export companion schema.json
    schema_info = {col: str(df[col].dtype) for col in df.columns}
    schema_path = target_path.parent / "schema.json"
    schema_path.write_text(json.dumps(schema_info, indent=2), encoding="utf-8")

    return target_path


def load_ledger_parquet(target_path: Path) -> pd.DataFrame:
    """Load Parquet ledger into DataFrame."""
    if not target_path.exists():
        raise FileNotFoundError(f"Parquet ledger not found at {target_path}")
    return pd.read_parquet(target_path)
