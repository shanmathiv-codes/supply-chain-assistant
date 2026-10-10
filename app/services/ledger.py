"""Local ledger service providing fast access to disruption cases and outcome aggregates."""
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_DB_PATH = Path("dataset/store/disruptions.db")
DEFAULT_PARQUET_PATH = Path("dataset/processed/cases_clean.parquet")


class LedgerService:
    """Provides indexed lookups and statistical aggregation over the disruption ledger."""

    def __init__(self, db_path: Path | None = None, parquet_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.parquet_path = parquet_path or DEFAULT_PARQUET_PATH
        self._df: pd.DataFrame | None = None

    def _get_df(self) -> pd.DataFrame:
        if self._df is None:
            if self.parquet_path.exists():
                self._df = pd.read_parquet(self.parquet_path)
            elif self.db_path.exists():
                with sqlite3.connect(str(self.db_path)) as conn:
                    self._df = pd.read_sql_query("SELECT * FROM disruptions", conn)
            else:
                self._df = pd.DataFrame()
        return self._df

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """Fetch a single disruption case by ID."""
        if not self.db_path.exists():
            df = self._get_df()
            if not df.empty and "disruption_id" in df.columns:
                match = df[df["disruption_id"] == case_id]
                if not match.empty:
                    return match.iloc[0].to_dict()
            return None

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM disruptions WHERE disruption_id = ?", (case_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                if "has_backup_supplier" in d and isinstance(d["has_backup_supplier"], int):
                    d["has_backup_supplier"] = bool(d["has_backup_supplier"])
                if "permanent_supplier_change" in d and isinstance(d["permanent_supplier_change"], int):
                    d["permanent_supplier_change"] = bool(d["permanent_supplier_change"])
                return d
        return None

    def get_cases_batch(self, case_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch a list of disruption records preserving the order of case_ids."""
        if not case_ids:
            return []
        cases = []
        for cid in case_ids:
            rec = self.get_case(cid)
            if rec:
                cases.append(rec)
        return cases

    def compute_analog_stats(self, case_ids: list[str]) -> dict[str, Any]:
        """Compute sample statistics (n, median, p10, p90) for retrieved cases."""
        cases = self.get_cases_batch(case_ids)
        if not cases:
            return {
                "n": 0,
                "median": 0.0,
                "p10": 0.0,
                "p90": 0.0,
                "case_ids": [],
            }

        recovery_days = [
            float(c["full_recovery_days"])
            for c in cases
            if c.get("full_recovery_days") is not None
        ]
        if not recovery_days:
            return {
                "n": len(cases),
                "median": 0.0,
                "p10": 0.0,
                "p90": 0.0,
                "case_ids": [c["disruption_id"] for c in cases],
            }

        arr = np.array(recovery_days)
        return {
            "n": len(recovery_days),
            "median": round(float(np.median(arr)), 1),
            "p10": round(float(np.percentile(arr, 10)), 1),
            "p90": round(float(np.percentile(arr, 90)), 1),
            "case_ids": [c["disruption_id"] for c in cases],
        }

    def compute_full_ledger_stats(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Compute population statistics over the full historical dataset matching filters."""
        df = self._get_df()
        if df.empty:
            return {"n": 0, "median": None}

        filtered = df
        for col, val in filters.items():
            if val is not None and col in filtered.columns:
                filtered = filtered[filtered[col] == val]

        if filtered.empty or "full_recovery_days" not in filtered.columns:
            return {"n": 0, "median": None}

        recovery_vals = filtered["full_recovery_days"].dropna()
        if recovery_vals.empty:
            return {"n": 0, "median": None}

        return {
            "n": len(recovery_vals),
            "median": round(float(recovery_vals.median()), 1),
            "p10": round(float(recovery_vals.quantile(0.10)), 1),
            "p90": round(float(recovery_vals.quantile(0.90)), 1),
        }

    def compute_outcomes_by_response(self, case_ids: list[str]) -> list[dict[str, Any]]:
        """Compute aggregated outcomes grouped by response_type for historical cases."""
        cases = self.get_cases_batch(case_ids)
        if not cases:
            return []

        df = pd.DataFrame(cases)
        if "response_type" not in df.columns or "full_recovery_days" not in df.columns:
            return []

        grouped = (
            df.groupby("response_type")
            .agg(
                n=("full_recovery_days", "count"),
                median_recovery=("full_recovery_days", "median"),
                min_recovery=("full_recovery_days", "min"),
                max_recovery=("full_recovery_days", "max"),
            )
            .reset_index()
        )

        results = []
        for _, row in grouped.iterrows():
            results.append({
                "response_type": str(row["response_type"]),
                "n": int(row["n"]),
                "median_full_recovery_days": round(float(row["median_recovery"]), 1),
                "min_full_recovery_days": round(float(row["min_recovery"]), 1),
                "max_full_recovery_days": round(float(row["max_recovery"]), 1),
            })
        return results


ledger_service = LedgerService()
