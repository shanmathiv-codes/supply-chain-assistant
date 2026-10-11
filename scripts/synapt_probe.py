"""Probe script inspecting Synapt MCP endpoint, authentication, schema, and content state."""

import asyncio
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.substrate.auth import synapt_auth_client
from app.substrate.gateway import SynaptReadGateway
from app.substrate.mcp_adapter import McpSubstrateAdapter


async def run_probe():
    print("=== Synapt Context Substrate Probe ===")

    # 1. Check credentials
    auth_mode = synapt_auth_client.auth_mode
    if auth_mode == "none":
        print(
            "\n[NOTICE] Missing Synapt credentials in .env.\n"
            "To probe a live Synapt provider, provide in .env:\n"
            "  SYNAPT_AGENT_CLIENT_ID=<id>\n"
            "  SYNAPT_AGENT_CLIENT_SECRET=<secret>\n"
            "  SYNAPT_PROVIDER_ID=<provider_id>\n"
            "Operating with MOCK substrate fallback.\n"
        )
        sys.exit(0)

    print(f"Connecting to Synapt MCP endpoint: {settings.synapt_mcp_url}")
    print(f"Client ID: {synapt_auth_client.client_id} (auth mode: {auth_mode})")
    print(f"Target Provider ID: {settings.synapt_provider_id}")

    # 2. Authenticate
    token = None
    try:
        token = await synapt_auth_client.get_token()
    except Exception as e:
        print(f"[ERROR] Failed to acquire token: {e}")

    if not token:
        print(
            "[NOTICE] Authentication to Synapt service failed.\n"
            "Operating in fallback mode (MOCK substrate)."
        )
        gw = SynaptReadGateway(mode="mock")
        stats = await gw.get_stats()
        schema = await gw.get_schema()
        episodes_data = await gw.episodes()
        case_count = stats.get("counts_by_label", {}).get("SupplyChainDisruption", 0)
        content_state = "cases_present" if case_count > 0 else "empty"
    else:
        print("[OK] Authentication successful; Bearer token acquired.")
        if synapt_auth_client.scope is not None:
            print(f"[OK] Granted Scope: {synapt_auth_client.scope}")

        # 3. Connect to live MCP session
        adapter = McpSubstrateAdapter()
        try:
            await adapter.health()
            tools = await adapter.list_tools()
            tool_names = [t["name"] for t in tools]
            print(
                f"[OK] Live MCP session initialized. Tools available ({len(tools)}): {', '.join(tool_names)}"
            )

            stats = await adapter.get_stats(provider_id=settings.synapt_provider_id or "")
            schema = await adapter.get_schema(provider_id=settings.synapt_provider_id or "")
            episodes_data = await adapter.episodes(provider_id=settings.synapt_provider_id or "")

            counts_by_label = stats.get("counts_by_label", {}) if isinstance(stats, dict) else {}
            case_count = (
                counts_by_label.get("SupplyChainDisruption", 0)
                if isinstance(counts_by_label, dict)
                else 0
            )

            # Check if tools returned RBAC/grant restriction
            stats_raw = str(stats)
            if "has no access to" in stats_raw:
                print(f"\n[NOTICE] Synapt Grant Pending: {stats_raw[:160]}")
                print(
                    "  The agent authenticated successfully, but tool access grants on this provider"
                )
                print("  are pending approval in the Synapt console / platform team.")
                content_state = "grant_pending"
            elif case_count >= 400:
                content_state = "cases_present"
            elif case_count > 0:
                content_state = "partial"
            elif schema.get("node_types") and case_count == 0:
                content_state = "schema_only"
            else:
                content_state = "connected_empty"

            await adapter.aclose()
        except Exception as e:
            print(f"[ERROR] Live MCP session error: {e}. Falling back to mock substrate.")
            gw = SynaptReadGateway(mode="mock")
            stats = await gw.get_stats()
            schema = await gw.get_schema()
            episodes_data = await gw.episodes()
            case_count = stats.get("counts_by_label", {}).get("SupplyChainDisruption", 0)
            content_state = "mock_fallback"

    print(f"\nSubstrate Content State detected: {content_state.upper()} (cases={case_count})")

    # 4. Write docs/SYNAPT_NOTES.md
    docs_dir = ROOT_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    notes_file = docs_dir / "SYNAPT_NOTES.md"

    notes_content = f"""# Synapt Integration & Schema Probe Notes

## Probe Execution
- **Timestamp:** {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
- **Client ID:** `{synapt_auth_client.client_id}`
- **Provider ID:** `{settings.synapt_provider_id}`
- **Substrate Content State:** `{content_state}`
- **Reported Cases:** {case_count}
- **Auth Mode:** `{auth_mode}`

## Live Tool Introspection
- **MCP Endpoint:** `{settings.synapt_mcp_url}`
- **Granted Scope:** `{synapt_auth_client.scope if synapt_auth_client.scope is not None else "full"}`

## Node Types and Properties
- **Node Labels:** {", ".join(schema.get("node_types", []))}
- **Relationship Types:** {", ".join(schema.get("edge_types", []))}
- **Properties Found:** {", ".join(schema.get("properties", []))}

## Ticket Store & Episode Capabilities
- **Has Ticket Store:** {stats.get("has_ticket_store", False) if isinstance(stats, dict) else False}
- **Episodes Health:** {episodes_data.get("status", "unknown") if isinstance(episodes_data, dict) else "unknown"}
"""
    notes_file.write_text(notes_content, encoding="utf-8")
    print(f"Notes written to {notes_file}")


def main():
    asyncio.run(run_probe())


if __name__ == "__main__":
    main()
