"""SQLite I/O operations mirroring ledger and providing quick relational lookups."""

import sqlite3
from pathlib import Path

import pandas as pd


def mirror_ledger_to_sqlite(df: pd.DataFrame, db_path: Path):
    """Write cleaned cases to SQLite disruptions.db indexed by disruption_id."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        df.to_sql("disruptions", conn, if_exists="replace", index=False)
        # Create index on disruption_id
        conn.execute("CREATE INDEX IF NOT EXISTS idx_disruption_id ON disruptions(disruption_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON disruptions(disruption_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON disruptions(disruption_severity);")
        conn.commit()


def get_case_by_id(db_path: Path, case_id: str) -> dict | None:
    """Fetch single disruption record by ID from SQLite."""
    if not db_path.exists():
        return None
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM disruptions WHERE disruption_id = ?", (case_id,))
        row = cur.fetchone()
        return dict(row) if row else None
