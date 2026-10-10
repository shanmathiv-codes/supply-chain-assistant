"""Replay Substrate Adapter reading pre-recorded fixtures."""
import hashlib
import json
from pathlib import Path
from typing import Any

from app.schemas.evidence import Evidence


class ReplaySubstrateAdapter:
    """Substrate adapter that replays recorded JSON responses from fixtures directory."""

    def __init__(self, fixtures_dir: Path | None = None):
        self.fixtures_dir = fixtures_dir or Path("fixtures/synapt/real")

    def _hash_params(self, params: dict[str, Any]) -> str:
        s = json.dumps(params, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def _load_fixture(self, tool_name: str, params: dict[str, Any]) -> Any:
        h = self._hash_params(params)
        target = self.fixtures_dir / tool_name / f"{h}.json"
        if not target.exists():
            # If specific hash not found, look for any default fixture in tool dir
            tool_dir = self.fixtures_dir / tool_name
            if tool_dir.exists():
                files = list(tool_dir.glob("*.json"))
                if files:
                    return json.loads(files[0].read_text(encoding="utf-8"))
            raise FileNotFoundError(
                f"Missing replay fixture for tool '{tool_name}' with params hash '{h}'. "
                f"Run 'python -m scripts.dev record-fixtures' to capture real fixtures."
            )
        return json.loads(target.read_text(encoding="utf-8"))

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "mode": "replay"}

    async def get_stats(self, provider_id: str = "") -> dict[str, Any]:
        return self._load_fixture("trident_get_stats", {"provider_id": provider_id})

    async def get_schema(self, provider_id: str = "") -> dict[str, Any]:
        return self._load_fixture("trident_get_schema", {"provider_id": provider_id})

    async def find_exact(self, label: str, provider_id: str = "") -> list[Evidence]:
        data = self._load_fixture("trident_find_exact", {"label": label, "provider_id": provider_id})
        return [Evidence(**item) for item in data]

    async def search_nodes(self, query: str, top_k: int = 5, provider_id: str = "") -> list[Evidence]:
        data = self._load_fixture("trident_search", {"query": query, "top_k": top_k, "provider_id": provider_id})
        return [Evidence(**item) for item in data]

    async def get_chunks(self, query: str, top_k: int = 5, provider_id: str = "") -> list[Evidence]:
        data = self._load_fixture("trident_get_chunks", {"query": query, "top_k": top_k, "provider_id": provider_id})
        return [Evidence(**item) for item in data]

    async def query(self, query_text: str, top_k: int = 5, provider_id: str = "") -> dict[str, Any]:
        res = self._load_fixture("trident_query", {"query": query_text, "top_k": top_k, "provider_id": provider_id})
        if "evidence" in res and isinstance(res["evidence"], list):
            res["evidence"] = [Evidence(**e) for e in res["evidence"]]
        return res

    async def label_ticket(self, ticket_text: str, provider_id: str = "") -> dict[str, Any]:
        return self._load_fixture("trident_label_ticket", {"ticket_text": ticket_text, "provider_id": provider_id})

    async def cypher(self, template_name: str, params: dict[str, Any], provider_id: str = "") -> list[dict[str, Any]]:
        return self._load_fixture(f"cypher_{template_name}", {"params": params, "provider_id": provider_id})

    async def get_node(self, node_id: str, depth: int = 1, provider_id: str = "") -> dict[str, Any]:
        return self._load_fixture("trident_get_node", {"node_id": node_id, "depth": depth, "provider_id": provider_id})

    async def traverse(self, start_node_id: str, edge_types: list[str], provider_id: str = "") -> list[dict[str, Any]]:
        return self._load_fixture("trident_traverse", {"start_node_id": start_node_id, "edge_types": edge_types, "provider_id": provider_id})

    async def get_procedures(self, query: str, provider_id: str = "") -> list[Evidence]:
        data = self._load_fixture("trident_get_procedures", {"query": query, "provider_id": provider_id})
        return [Evidence(**item) for item in data]

    async def episodes(self, query: str | None = None, episode_id: str | None = None, provider_id: str = "") -> dict[str, Any]:
        return self._load_fixture("trident_episodes", {"query": query, "episode_id": episode_id, "provider_id": provider_id})
