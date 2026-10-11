# -*- coding: utf-8 -*-
"""Query the context provider through the MCP endpoint as the registered agent.

python query.py "what are the main procedures in this knowledge base?"
python query.py "..." --raw --top-k 8
python query.py --whoami          # prove identity, show granted scope + tools
python query.py --stats           # graph stats for the provider
python query.py "..." --mode chunks
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx

# Substrate content is UTF-8 and routinely contains characters (arrows, dashes)
# that the default Windows console codepage cannot encode - without this, a
# perfectly good answer dies in print() with a UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

from query_agent import ConfigError, MCPError, QueryAgent, TokenError

DEFAULT_QUESTION = "What are the main procedures and rules in this knowledge base?"


def show(label: str, obj, limit: int = 6000) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str)[:limit])


async def main_async(ns: argparse.Namespace) -> int:
    agent = QueryAgent.from_env()

    if ns.provider_id:
        agent.cfg.provider_id = agent.mcp.provider_id = ns.provider_id

    print(f"agent    : {agent.cfg.client_id} ({agent.cfg.auth_mode})")
    print(f"provider : {agent.cfg.provider_id}")
    print(f"mcp      : {agent.cfg.mcp_url}")

    async with agent:
        if ns.whoami:
            show("whoami", await agent.whoami())
            return 0

        if ns.stats:
            show("provider stats", await agent.stats())
            if not ns.question:
                return 0

        question = ns.question or DEFAULT_QUESTION

        if ns.mode == "chunks":
            show("chunks", await agent.chunks(question, top_k=ns.top_k))
            return 0
        if ns.mode == "search":
            show("search", await agent.search(question, top_k=ns.top_k))
            return 0
        if ns.mode == "procedures":
            show("procedures", await agent.procedures(question))
            return 0

        result = await agent.ask(question, top_k=ns.top_k, graph_hops=ns.graph_hops)
        if isinstance(result, dict) and result.get("answer") and not ns.raw:
            print("\n=== answer ===")
            print(result["answer"])
            if result.get("confidence") is not None:
                print(f"\nconfidence: {result['confidence']}")
            if ns.sources and result.get("sources"):
                show("sources", result["sources"])
        else:
            show("query", result)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("question", nargs="?", help="the question to ask")
    p.add_argument("--mode", choices=["query", "chunks", "search", "procedures"], default="query")
    p.add_argument("--provider-id", help="override SYNAPT_PROVIDER_ID for this call")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--graph-hops", type=int, default=2)
    p.add_argument(
        "--raw", action="store_true", help="print the whole response, not just the answer"
    )
    p.add_argument("--sources", action="store_true", help="also print the cited sources")
    p.add_argument("--stats", action="store_true", help="print the provider's graph stats")
    p.add_argument(
        "--whoami", action="store_true", help="check identity, show granted scope and tools"
    )
    ns = p.parse_args()
    try:
        return asyncio.run(main_async(ns))
    except (ConfigError, TokenError, MCPError, FileNotFoundError) as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1
    except httpx.ConnectError as exc:
        print(f"\nconnection error: {exc}", file=sys.stderr)
        if "CERTIFICATE_VERIFY" in str(exc):
            print("Set SYNAPT_VERIFY_SSL to a CA bundle path, or to 'false'.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
