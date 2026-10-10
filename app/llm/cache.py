"""SQLite LLM response caching layer for reproducibility and quota protection."""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import load_yaml_config

MODELS_CONFIG = load_yaml_config("models.yaml")
CACHE_DB_PATH = Path(MODELS_CONFIG.get("cache_db_path", "artifacts/cache/llm_cache.db"))


class LLMCache:
    """Persistent SQLite cache for LLM completion requests."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or CACHE_DB_PATH
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    role TEXT,
                    model TEXT,
                    prompt_name TEXT,
                    response_json TEXT,
                    tokens_used INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def _compute_key(
        self,
        role: str,
        model: str,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str:
        payload = {
            "role": role,
            "model": model,
            "prompt_name": prompt_name,
            "messages": messages,
            "temperature": temperature,
        }
        raw_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def get(
        self,
        role: str,
        model: str,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> dict[str, Any] | None:
        key = self._compute_key(role, model, prompt_name, messages, temperature)
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT response_json FROM response_cache WHERE cache_key = ?", (key,))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def put(
        self,
        role: str,
        model: str,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        response_data: dict[str, Any],
        tokens_used: int = 0,
    ):
        key = self._compute_key(role, model, prompt_name, messages, temperature)
        resp_json = json.dumps(response_data)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO response_cache (cache_key, role, model, prompt_name, response_json, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key, role, model, prompt_name, resp_json, tokens_used),
            )
            conn.commit()


llm_cache = LLMCache()
