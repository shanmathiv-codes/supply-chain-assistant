"""Real MCP Substrate Adapter using official mcp Python SDK."""

from typing import Any

import httpx

from app.core.config import load_yaml_config, settings
from app.core.ids import generate_evidence_id
from app.schemas.evidence import Evidence
from app.substrate.auth import synapt_auth_client

TOOLS_CONFIG = load_yaml_config("synapt_tools.yaml")


class McpSubstrateAdapter:
    """Substrate adapter talking to Synapt over MCP transport."""

    def __init__(self):
        self.base_url = settings.synapt_mcp_url
        self.provider_id = settings.synapt_provider_id or ""

    async def _get_headers(self) -> dict[str, str]:
        token = await synapt_auth_client.get_token()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool via HTTP/SSE transport."""
        url = self.base_url.rstrip("/") + f"/call/{tool_name}"
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(url, json={"arguments": arguments}, headers=headers)
            if resp.status_code == 401:
                # Refresh token and retry once
                token = await synapt_auth_client.get_token(force_refresh=True)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    resp = await client.post(url, json={"arguments": arguments}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("isError"):
                raise RuntimeError(f"MCP tool '{tool_name}' returned error: {data.get('content')}")
            return data.get("content", data)

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "mode": "mcp", "url": self.base_url}

    async def get_stats(self, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        return await self.call_tool("trident_get_stats", {"provider_id": p_id})

    async def get_schema(self, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        return await self.call_tool("trident_get_schema", {"provider_id": p_id})

    async def find_exact(self, label: str, provider_id: str = "") -> list[Evidence]:
        p_id = provider_id or self.provider_id
        res = await self.call_tool("trident_find_exact", {"label": label, "provider_id": p_id})
        # Parse content blocks into Evidence
        results = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_find_exact",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        node_id=item.get("node_id") if isinstance(item, dict) else None,
                        case_id=item.get("disruption_id") if isinstance(item, dict) else None,
                        text_span=str(item),
                        score=1.0,
                    )
                )
        return results

    async def search_nodes(
        self, query: str, top_k: int = 5, provider_id: str = ""
    ) -> list[Evidence]:
        p_id = provider_id or self.provider_id
        res = await self.call_tool(
            "trident_search", {"query": query, "top_k": top_k, "provider_id": p_id}
        )
        results = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_search",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        node_id=item.get("node_id") if isinstance(item, dict) else None,
                        case_id=item.get("disruption_id") if isinstance(item, dict) else None,
                        text_span=str(item),
                        score=item.get("score", 0.85) if isinstance(item, dict) else 0.85,
                    )
                )
        return results

    async def get_chunks(self, query: str, top_k: int = 5, provider_id: str = "") -> list[Evidence]:
        p_id = provider_id or self.provider_id
        res = await self.call_tool(
            "trident_get_chunks", {"query": query, "top_k": top_k, "provider_id": p_id}
        )
        results = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_get_chunks",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        chunk_id=item.get("chunk_id") if isinstance(item, dict) else None,
                        case_id=item.get("disruption_id") if isinstance(item, dict) else None,
                        text_span=item.get("text") if isinstance(item, dict) else str(item),
                        score=item.get("score", 0.80) if isinstance(item, dict) else 0.80,
                    )
                )
        return results

    async def query(self, query_text: str, top_k: int = 5, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        return await self.call_tool(
            "trident_query", {"query": query_text, "top_k": top_k, "provider_id": p_id}
        )

    async def label_ticket(self, ticket_text: str, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        return await self.call_tool(
            "trident_label_ticket", {"ticket_text": ticket_text, "provider_id": p_id}
        )

    async def cypher(
        self, template_name: str, params: dict[str, Any], provider_id: str = ""
    ) -> list[dict[str, Any]]:
        p_id = provider_id or self.provider_id
        return await self.call_tool(
            "trident_cypher", {"query": params.get("query"), "params": params, "provider_id": p_id}
        )

    async def get_node(self, node_id: str, depth: int = 1, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        return await self.call_tool(
            "trident_get_node", {"node_id": node_id, "depth": depth, "provider_id": p_id}
        )

    async def traverse(
        self, start_node_id: str, edge_types: list[str], provider_id: str = ""
    ) -> list[dict[str, Any]]:
        p_id = provider_id or self.provider_id
        return await self.call_tool(
            "trident_traverse",
            {"start_node_id": start_node_id, "edge_types": edge_types, "provider_id": p_id},
        )

    async def get_procedures(self, query: str, provider_id: str = "") -> list[Evidence]:
        p_id = provider_id or self.provider_id
        res = await self.call_tool("trident_get_procedures", {"query": query, "provider_id": p_id})
        results = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_get_procedures",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        doc_id=item.get("doc_id") if isinstance(item, dict) else None,
                        text_span=str(item),
                        score=0.90,
                    )
                )
        return results

    async def episodes(
        self, query: str | None = None, episode_id: str | None = None, provider_id: str = ""
    ) -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        args = {"provider_id": p_id}
        if query:
            args["query"] = query
        if episode_id:
            args["episode_id"] = episode_id
        return await self.call_tool("trident_episodes", args)
