"""SQLite persistence store for disruption investigation runs and reports."""

import json
import sqlite3
from pathlib import Path
from typing import Any

RUNS_DB_PATH = Path("dataset/store/app.db")


class RunStore:
    """Manages persistent storage and retrieval of completed disruption analysis reports."""

    def __init__(self, db_path: Path = RUNS_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    report_json TEXT,
                    summary TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    case_id TEXT,
                    kind TEXT,
                    value REAL,
                    comment TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def save_run(self, run_id: str, status: str, report_dict: dict[str, Any], summary: str = ""):
        """Persist a completed run report."""
        report_json = json.dumps(report_dict)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, status, report_json, summary) VALUES (?, ?, ?, ?)",
                (run_id, status, report_json, summary),
            )
            conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Fetch report JSON by run_id."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT report_json FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
        return None


run_store = RunStore()
