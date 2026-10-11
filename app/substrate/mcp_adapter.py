"""Real MCP Substrate Adapter using the official Python mcp SDK over Streamable HTTP."""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any

import httpx
from mcp import ClientSession

try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as streamable_http_client

from app.core.config import settings
from app.core.ids import generate_evidence_id
from app.core.logging import logger
from app.schemas.evidence import Evidence
from app.substrate.auth import synapt_auth_client


class MCPError(RuntimeError):
    """Transport failure, authorization error, or tool error."""


class McpSubstrateAdapter:
    """Substrate adapter connected to Trident MCP server via Streamable HTTP."""

    def __init__(self):
        self.base_url = settings.synapt_mcp_url.rstrip()
        self.provider_id = settings.synapt_provider_id or ""
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._timeout = float(settings.synapt_query_timeout)
        self._verify = settings.effective_synapt_verify

    async def __aenter__(self) -> McpSubstrateAdapter:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._stack is not None:
            try:
                await self._stack.aclose()
            except BaseException:
                pass
            finally:
                self._stack = None
                self._session = None

    async def connect(self, *, force_token: bool = False) -> None:
        """Establish or renew a long-lived Streamable HTTP MCP session."""
        await self.aclose()
        token = await synapt_auth_client.get_token(force_refresh=force_token)
        if not token:
            raise MCPError("Cannot open MCP session: no active Synapt token could be acquired.")

        stack = AsyncExitStack()
        try:
            http_client = await stack.enter_async_context(
                httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self._timeout,
                    verify=self._verify,
                )
            )
            read_stream, write_stream = await stack.enter_async_context(
                streamable_http_client(self.base_url, http_client=http_client)
            )
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            self._stack = stack
            self._session = session
            logger.info(f"Initialized MCP session to Synapt at {self.base_url}")
        except BaseException as exc:
            try:
                await stack.aclose()
            except BaseException:
                pass
            probe = await self._diagnose(token)
            err_msg = (
                f"Could not open MCP session at {self.base_url} [server said: {probe}] ({exc})"
            )
            logger.warning(err_msg)
            raise MCPError(err_msg) from exc

    async def _diagnose(self, token: str) -> str:
        """Issue direct probe to surface underlying HTTP status and error details."""
        body = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "scd-assistant", "version": "1.0"},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=self._verify) as http:
                resp = await http.post(
                    self.base_url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json, text/event-stream",
                    },
                )
            return f"HTTP {resp.status_code}: {resp.text[:200].strip()}"
        except Exception as exc:
            return f"probe failed: {exc}"

    # ── Input sanitization & response unwrapping ────────────────────────────

    @staticmethod
    def _sanitize(text: str) -> str:
        """Drop control characters that servers reject in JSON strings."""
        text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        return "".join(
            ch if (ord(ch) >= 0x20 and ord(ch) != 0x7F) or ch == "\t" else " " for ch in text
        )

    @staticmethod
    def _decode(value: Any) -> Any:
        """Decode double-encoded JSON returned as a string."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    @classmethod
    def _unwrap(cls, result: Any) -> Any:
        """Unwrap FastMCP structuredContent or text blocks into deserialized data."""
        structured = getattr(result, "structuredContent", None)
        if structured:
            if isinstance(structured, dict) and set(structured.keys()) == {"result"}:
                return cls._decode(structured["result"])
            return structured

        texts = [
            b.text
            for b in (getattr(result, "content", None) or [])
            if getattr(b, "type", None) == "text"
        ]
        if texts:
            joined = "\n".join(texts)
            return cls._decode(joined)
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Execute an MCP tool call with injected provider_id and auto-retry."""
        if self._session is None:
            await self.connect()
        assert self._session is not None

        args = arguments or {}
        clean_args = {
            k: (self._sanitize(v) if isinstance(v, str) else v)
            for k, v in args.items()
            if v is not None
        }
        # In the registered-agent flow, provider_id must be injected
        p_id = clean_args.get("provider_id") or self.provider_id
        if p_id:
            clean_args["provider_id"] = p_id

        # Never pass client_id or agent_id in tool arguments
        clean_args.pop("client_id", None)
        clean_args.pop("agent_id", None)

        try:
            result = await self._session.call_tool(tool_name, clean_args)
        except BaseException as exc:
            logger.info(
                f"MCP tool call '{tool_name}' failed ({exc}); reconnecting with fresh token..."
            )
            await self.connect(force_token=True)
            assert self._session is not None
            try:
                result = await self._session.call_tool(tool_name, clean_args)
            except BaseException as retry_exc:
                raise MCPError(f"Tool {tool_name} failed after retry: {retry_exc}") from exc

        unwrapped = self._unwrap(result)
        # Check if the tool reported access denial
        if isinstance(unwrapped, str) and "has no access to" in unwrapped:
            logger.warning(f"Synapt grant limitation for '{tool_name}': {unwrapped}")
        return unwrapped

    # ── High-Level Substrate Domain Methods ─────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Check live MCP session health and introspect available tools."""
        try:
            tools = await self.list_tools()
            return {
                "status": "ok",
                "mode": "mcp",
                "url": self.base_url,
                "provider_id": self.provider_id,
                "tools_count": len(tools),
                "tools": [t.get("name") for t in tools],
            }
        except Exception as e:
            return {"status": "degraded", "mode": "mcp", "url": self.base_url, "error": str(e)}

    async def list_tools(self) -> list[dict[str, Any]]:
        if self._session is None:
            await self.connect()
        assert self._session is not None
        res = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "schema": getattr(t, "input_schema", getattr(t, "inputSchema", {})),
            }
            for t in res.tools
        ]

    async def get_stats(self, provider_id: str = "") -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        res = await self.call_tool("trident_get_stats", {"provider_id": p_id})
        return res if isinstance(res, dict) else {"counts_by_label": {}, "raw": str(res)}

    async def get_schema(self, provider_id: str = "") -> dict[str, Any]:
        """Derive schema information from get_stats since trident_get_schema is not granted."""
        stats = await self.get_stats(provider_id=provider_id)
        counts = stats.get("counts_by_label", {}) if isinstance(stats, dict) else {}
        node_types = (
            list(counts.keys()) if counts else ["SupplyChainDisruption", "DisruptionIncident"]
        )
        return {
            "node_types": node_types,
            "edge_types": ["CAUSES", "AFFECTS", "RECOVERS_WITH", "LOCATED_IN"],
            "properties": ["disruption_type", "severity", "recovery_days", "supplier_tier"],
            "has_ticket_store": stats.get("has_ticket_store", False)
            if isinstance(stats, dict)
            else False,
        }

    async def search_nodes(
        self, query: str, top_k: int = 5, node_type: str | None = None, provider_id: str = ""
    ) -> list[Evidence]:
        p_id = provider_id or self.provider_id
        args: dict[str, Any] = {"query": query, "top_k": top_k, "provider_id": p_id}
        if node_type:
            args["node_type"] = node_type

        res = await self.call_tool("trident_search", args)
        results: list[Evidence] = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_search",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        node_id=item.get("node_id") if isinstance(item, dict) else None,
                        case_id=item.get("disruption_id") or item.get("case_id")
                        if isinstance(item, dict)
                        else None,
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
        results: list[Evidence] = []
        if isinstance(res, list):
            for item in res:
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_get_chunks",
                        provider_id=p_id,
                        provenance_mode="MCP",
                        chunk_id=item.get("chunk_id") if isinstance(item, dict) else None,
                        case_id=item.get("disruption_id") or item.get("case_id")
                        if isinstance(item, dict)
                        else None,
                        text_span=item.get("text") if isinstance(item, dict) else str(item),
                        score=item.get("score", 0.80) if isinstance(item, dict) else 0.80,
                    )
                )
        return results

    async def query(
        self, query_text: str, top_k: int = 5, graph_hops: int = 2, provider_id: str = ""
    ) -> dict[str, Any]:
        """Ask lane query using trident_query (requires question argument)."""
        p_id = provider_id or self.provider_id
        res = await self.call_tool(
            "trident_query",
            {"question": query_text, "top_k": top_k, "graph_hops": graph_hops, "provider_id": p_id},
        )
        if isinstance(res, dict):
            return res
        return {"answer": str(res), "confidence": 0.85, "chunks": []}

    async def get_procedures(
        self, query: str | None = None, provider_id: str = ""
    ) -> list[Evidence]:
        p_id = provider_id or self.provider_id
        args: dict[str, Any] = {"provider_id": p_id}
        if query:
            args["query"] = query
        res = await self.call_tool("trident_get_procedures", args)
        results: list[Evidence] = []
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

    async def traverse(
        self,
        node_id: str,
        edge_types: list[str] | None = None,
        node_types: list[str] | None = None,
        direction: str | None = None,
        depth: int | None = None,
        provider_id: str = "",
    ) -> list[dict[str, Any]]:
        p_id = provider_id or self.provider_id
        args: dict[str, Any] = {"node_id": node_id, "provider_id": p_id}
        if edge_types:
            args["edge_types"] = edge_types
        if node_types:
            args["node_types"] = node_types
        if direction:
            args["direction"] = direction
        if depth:
            args["depth"] = depth
        res = await self.call_tool("trident_traverse", args)
        return res if isinstance(res, list) else []

    async def episodes(
        self, query: str | None = None, episode_id: str | None = None, provider_id: str = ""
    ) -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        args: dict[str, Any] = {"provider_id": p_id}
        if query:
            args["query"] = query
        if episode_id:
            args["episode_id"] = episode_id
        res = await self.call_tool("trident_episodes", args)
        return res if isinstance(res, dict) else {"status": "ok", "raw": str(res)}

    async def feedback(
        self,
        feedback_id: str,
        caller_type: str | None = None,
        verdict: Any = None,
        post_action: Any = None,
        score: Any = None,
        reason: str | None = None,
        provider_id: str = "",
    ) -> dict[str, Any]:
        p_id = provider_id or self.provider_id
        args: dict[str, Any] = {"feedback_id": feedback_id, "provider_id": p_id}
        if caller_type:
            args["caller_type"] = caller_type
        if verdict is not None:
            args["verdict"] = verdict
        if post_action is not None:
            args["post_action"] = post_action
        if score is not None:
            args["score"] = score
        if reason:
            args["reason"] = reason
        res = await self.call_tool("trident_feedback", args)
        return res if isinstance(res, dict) else {"status": "ok", "result": res}

    # ── Graceful Fallback for Tools Outside Registered Grant ───────────────

    async def find_exact(self, label: str, provider_id: str = "") -> list[Evidence]:
        """trident_find_exact is not in registered agent grant; fall back to trident_search."""
        return await self.search_nodes(query=label, top_k=3, provider_id=provider_id)

    async def cypher(
        self, template_name: str, params: dict[str, Any], provider_id: str = ""
    ) -> list[dict[str, Any]]:
        """trident_cypher is not in registered agent grant; return empty list gracefully."""
        logger.debug(f"Cypher template '{template_name}' bypassed (not in registered agent grant).")
        return []

    async def label_ticket(self, ticket_text: str, provider_id: str = "") -> dict[str, Any]:
        """trident_label_ticket is not in registered agent grant; return empty mapping."""
        return {}
