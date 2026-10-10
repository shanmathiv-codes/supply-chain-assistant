"""Substrate Gateway classes enforcing permission tiers, caching, traces, and resilience."""
import hashlib
import json
import time
from typing import Any

from app.core.config import settings
from app.core.logging import correlation_id_ctx, logger
from app.schemas.evidence import Evidence, SubstrateCall
from app.substrate.mcp_adapter import McpSubstrateAdapter
from app.substrate.mock_adapter import MockSubstrateAdapter
from app.substrate.replay_adapter import ReplaySubstrateAdapter


class CircuitBreaker:
    """Basic circuit breaker guarding external substrate calls."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN


class SynaptReadGateway:
    """Read-tier gateway: provides read-only substrate inspection and query methods."""

    def __init__(self, mode: str | None = None):
        self._mode_override = mode
        self._adapter = None
        self.circuit_breaker = CircuitBreaker()
        self._read_cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl = 30.0  # seconds

    @property
    def mode(self) -> str:
        return self._mode_override or settings.effective_synapt_mode

    @property
    def adapter(self):
        curr_mode = self.mode
        if curr_mode == "mcp":
            if not isinstance(self._adapter, McpSubstrateAdapter):
                self._adapter = McpSubstrateAdapter()
        elif curr_mode == "replay":
            if not isinstance(self._adapter, ReplaySubstrateAdapter):
                self._adapter = ReplaySubstrateAdapter()
        else:
            if not isinstance(self._adapter, MockSubstrateAdapter):
                self._adapter = MockSubstrateAdapter()
        return self._adapter

    def _hash_call(self, tool: str, params: dict[str, Any]) -> str:
        s = json.dumps({"tool": tool, "params": params}, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    async def _execute(
        self,
        tool: str,
        method_name: str,
        params: dict[str, Any],
        trace_collector: list[SubstrateCall] | None = None,
        template_name: str | None = None,
    ) -> Any:
        params_hash = self._hash_call(tool, params)
        now = time.time()

        # Check TTL cache
        if params_hash in self._read_cache:
            ts, val = self._read_cache[params_hash]
            if now - ts < self._cache_ttl:
                return val

        if not self.circuit_breaker.allow_request():
            err_msg = "Substrate circuit breaker is OPEN due to repeated upstream failures."
            if trace_collector is not None:
                trace_collector.append(
                    SubstrateCall(
                        tool=tool,
                        params_hash=params_hash,
                        template=template_name,
                        latency_ms=0.0,
                        rows=0,
                        ok=False,
                        error=err_msg,
                        correlation_id=correlation_id_ctx.get(),
                    )
                )
            raise RuntimeError(err_msg)

        t_start = time.perf_counter()
        ok = True
        error = None
        result = None
        rows = 0

        try:
            fn = getattr(self.adapter, method_name)
            result = await fn(**params)
            self.circuit_breaker.record_success()
            if isinstance(result, list):
                rows = len(result)
            elif isinstance(result, dict):
                rows = 1
            # Cache successful read
            self._read_cache[params_hash] = (now, result)
        except Exception as exc:
            ok = False
            error = str(exc)
            self.circuit_breaker.record_failure()
            logger.warning(f"Substrate call '{tool}' failed: {exc}")
            raise
        finally:
            latency = (time.perf_counter() - t_start) * 1000.0
            call_record = SubstrateCall(
                tool=tool,
                params_hash=params_hash,
                template=template_name,
                latency_ms=round(latency, 2),
                rows=rows,
                ok=ok,
                error=error,
                query_ref=result.get("query_ref") if isinstance(result, dict) else None,
                correlation_id=correlation_id_ctx.get(),
            )
            if trace_collector is not None:
                trace_collector.append(call_record)

        return result

    async def health(self) -> dict[str, Any]:
        return await self.adapter.health()

    async def get_stats(self, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_get_stats", "get_stats", {"provider_id": provider_id}, trace)

    async def get_schema(self, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_get_schema", "get_schema", {"provider_id": provider_id}, trace)

    async def find_exact(self, label: str, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[Evidence]:
        return await self._execute("trident_find_exact", "find_exact", {"label": label, "provider_id": provider_id}, trace)

    async def search_nodes(self, query: str, top_k: int = 5, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[Evidence]:
        return await self._execute("trident_search", "search_nodes", {"query": query, "top_k": top_k, "provider_id": provider_id}, trace)

    async def get_chunks(self, query: str, top_k: int = 5, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[Evidence]:
        return await self._execute("trident_get_chunks", "get_chunks", {"query": query, "top_k": top_k, "provider_id": provider_id}, trace)

    async def query(self, query_text: str, top_k: int = 5, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_query", "query", {"query_text": query_text, "top_k": top_k, "provider_id": provider_id}, trace)

    async def label_ticket(self, ticket_text: str, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_label_ticket", "label_ticket", {"ticket_text": ticket_text, "provider_id": provider_id}, trace)

    async def cypher(self, template_name: str, params: dict[str, Any], provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[dict[str, Any]]:
        return await self._execute(
            "trident_cypher",
            "cypher",
            {"template_name": template_name, "params": params, "provider_id": provider_id},
            trace,
            template_name=template_name,
        )

    async def get_node(self, node_id: str, depth: int = 1, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_get_node", "get_node", {"node_id": node_id, "depth": depth, "provider_id": provider_id}, trace)

    async def traverse(self, start_node_id: str, edge_types: list[str], provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[dict[str, Any]]:
        return await self._execute("trident_traverse", "traverse", {"start_node_id": start_node_id, "edge_types": edge_types, "provider_id": provider_id}, trace)

    async def get_procedures(self, query: str, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> list[Evidence]:
        return await self._execute("trident_get_procedures", "get_procedures", {"query": query, "provider_id": provider_id}, trace)

    async def episodes(self, query: str | None = None, episode_id: str | None = None, provider_id: str = "", trace: list[SubstrateCall] | None = None) -> dict[str, Any]:
        return await self._execute("trident_episodes", "episodes", {"query": query, "episode_id": episode_id, "provider_id": provider_id}, trace)


class SynaptFeedbackGateway:
    """Feedback-tier gateway: records user feedback via trident_feedback."""

    def __init__(self, mode: str | None = None):
        self.mode = mode or settings.effective_synapt_mode

    async def feedback(self, query_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "mock":
            return {"status": "recorded_mock", "query_ref": query_ref}
        return {"status": "recorded", "query_ref": query_ref}


class SynaptAdminGateway:
    """Admin-tier gateway: provides ingestion methods. Forbidden from app/api and app/workflow."""

    def __init__(self, mode: str | None = None):
        self.mode = mode or settings.effective_synapt_mode

    async def ingest(self, spec: dict[str, Any]) -> str:
        req_id = f"req-ingest-{int(time.time())}"
        print(f"[AdminGateway] Ingest submitted: connector={spec.get('connector_type')} -> {req_id}")
        return req_id
