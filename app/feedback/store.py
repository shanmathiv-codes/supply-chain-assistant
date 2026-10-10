"""Feedback and Actual Outcomes Persistence Store.

Manages SQLite tables for user ratings, actual observed outcomes, and the human review queue.
Ensures unreviewed feedback is never treated as ground truth.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings

FEEDBACK_DB_PATH = Path("dataset/store/feedback.db")


class FeedbackStore:
    """SQLite feedback store for user feedback and actual operational outcomes."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            settings = get_settings()
            self.db_path = Path(getattr(settings, "feedback_db_path", FEEDBACK_DB_PATH))
        else:
            self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    case_id TEXT,
                    kind TEXT NOT NULL,
                    value REAL,
                    comment TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                );

                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    actual_production_impact_pct REAL,
                    actual_revenue_loss_usd REAL,
                    actual_full_recovery_days REAL,
                    actual_response_type TEXT,
                    simulated INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reviewer_notes TEXT,
                    reviewed_at TEXT
                );
            """)

    def record_feedback(
        self,
        run_id: str,
        kind: str,
        value: float | None = None,
        case_id: str | None = None,
        comment: str | None = None,
    ) -> int:
        """Record human feedback with status='pending' and queue for review."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO feedback (run_id, case_id, kind, value, comment, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (run_id, case_id, kind, value, comment, now),
            )
            feedback_id = cur.lastrowid
            assert feedback_id is not None
            conn.execute(
                """
                INSERT INTO review_queue (item_type, item_id, status)
                VALUES ('feedback', ?, 'pending')
                """,
                (feedback_id,),
            )
            return feedback_id

    def record_outcome(
        self,
        run_id: str,
        actual_production_impact_pct: float | None = None,
        actual_revenue_loss_usd: float | None = None,
        actual_full_recovery_days: float | None = None,
        actual_response_type: str | None = None,
        simulated: bool = False,
    ) -> int:
        """Record actual operational outcome with status='pending' and queue for review."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO outcomes (
                    run_id, actual_production_impact_pct, actual_revenue_loss_usd,
                    actual_full_recovery_days, actual_response_type, simulated, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    run_id,
                    actual_production_impact_pct,
                    actual_revenue_loss_usd,
                    actual_full_recovery_days,
                    actual_response_type,
                    1 if simulated else 0,
                    now,
                ),
            )
            outcome_id = cur.lastrowid
            assert outcome_id is not None
            conn.execute(
                """
                INSERT INTO review_queue (item_type, item_id, status)
                VALUES ('outcome', ?, 'pending')
                """,
                (outcome_id,),
            )
            return outcome_id

    def list_pending(self) -> list[dict[str, Any]]:
        """List all pending items in the review queue."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT q.id as queue_id, q.item_type, q.item_id, q.status,
                       f.run_id as f_run_id, f.kind, f.value, f.comment, f.created_at as f_created,
                       o.run_id as o_run_id, o.actual_production_impact_pct, o.actual_revenue_loss_usd,
                       o.actual_full_recovery_days, o.simulated, o.created_at as o_created
                FROM review_queue q
                LEFT JOIN feedback f ON q.item_type = 'feedback' AND q.item_id = f.id
                LEFT JOIN outcomes o ON q.item_type = 'outcome' AND q.item_id = o.id
                WHERE q.status = 'pending'
                ORDER BY q.id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def review_item(self, queue_id: int, action: str, notes: str | None = None) -> bool:
        """Approve or reject an item in the review queue."""
        if action not in ("approve", "reject"):
            raise ValueError(f"Invalid review action: {action}")
        new_status = "approved" if action == "approve" else "rejected"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT item_type, item_id FROM review_queue WHERE id = ?",
                (queue_id,),
            ).fetchone()
            if not row:
                return False

            item_type, item_id = row["item_type"], row["item_id"]

            # Update review queue
            conn.execute(
                """
                UPDATE review_queue
                SET status = ?, reviewer_notes = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (new_status, notes, now, queue_id),
            )

            # Update underlying record
            table = "feedback" if item_type == "feedback" else "outcomes"
            conn.execute(
                f"UPDATE {table} SET status = ? WHERE id = ?",
                (new_status, item_id),
            )
            return True

    def get_approved_outcomes(self, include_simulated: bool = True) -> list[dict[str, Any]]:
        """Retrieve approved actual outcomes for retraining or evaluation."""
        with self._get_connection() as conn:
            query = "SELECT * FROM outcomes WHERE status = 'approved'"
            if not include_simulated:
                query += " AND simulated = 0"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def get_approved_feedback(self) -> list[dict[str, Any]]:
        """Retrieve approved user feedback."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM feedback WHERE status = 'approved'").fetchall()
            return [dict(r) for r in rows]
