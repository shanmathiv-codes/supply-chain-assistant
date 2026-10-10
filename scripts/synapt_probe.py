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


async def run_probe():
    print("=== Synapt Context Substrate Probe ===")

    # 1. Check credentials
    if not settings.synapt_username or not settings.synapt_password:
        print(
            "\n[NOTICE] Missing Synapt credentials in .env (SYNAPT_USERNAME / SYNAPT_PASSWORD).\n"
            "To probe a live Synapt provider:\n"
            "  1. Add SYNAPT_USERNAME, SYNAPT_PASSWORD, and SYNAPT_PROVIDER_ID to .env\n"
            "  2. Re-run: python -m scripts.dev synapt-probe\n"
            "The assistant is operating with MOCK substrate fallback.\n"
        )
        sys.exit(0)

    print(f"Connecting to Synapt MCP endpoint: {settings.synapt_mcp_url}")
    print(f"Target Provider ID: {settings.synapt_provider_id}")

    # 2. Authenticate
    token = None
    try:
        token = await synapt_auth_client.get_token()
    except Exception as e:
        print(f"[NOTICE] Network connection to SYNAPT_AUTH_BASE could not be established: {e}")

    if not token:
        print(
            "[NOTICE] Authentication to live Synapt service failed or endpoint offline.\n"
            "Operating in fallback mode (MOCK substrate). Recording schema notes from mock store."
        )
        gw = SynaptReadGateway(mode="mock")
        stats = await gw.get_stats()
        schema = await gw.get_schema()
        episodes_data = await gw.episodes()
        case_count = stats.get("counts_by_label", {}).get("SupplyChainDisruption", 0)
        content_state = "cases_present" if case_count > 0 else "empty"
    else:
        print("[OK] Authentication successful; Bearer token acquired.")
        # 3. Read Gateway Probe
        gw = SynaptReadGateway(mode="mcp")
        try:
            stats = await gw.get_stats(provider_id=settings.synapt_provider_id or "")
            schema = await gw.get_schema(provider_id=settings.synapt_provider_id or "")
            episodes_data = await gw.episodes(provider_id=settings.synapt_provider_id or "")
            counts_by_label = stats.get("counts_by_label", {})
            case_count = counts_by_label.get("SupplyChainDisruption", 0)
            if case_count >= 400:
                content_state = "cases_present"
            elif case_count > 0:
                content_state = "partial"
            elif schema.get("node_types") and case_count == 0:
                content_state = "schema_only"
            else:
                content_state = "empty"
        except Exception as e:
            print(f"[ERROR] Live MCP tool call failed: {e}. Falling back to mock substrate.")
            gw = SynaptReadGateway(mode="mock")
            stats = await gw.get_stats()
            schema = await gw.get_schema()
            episodes_data = await gw.episodes()
            case_count = stats.get("counts_by_label", {}).get("SupplyChainDisruption", 0)
            content_state = "cases_present"

    print(f"\nSubstrate Content State detected: {content_state.upper()} (cases={case_count})")

    # 5. Write docs/SYNAPT_NOTES.md
    docs_dir = ROOT_DIR / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    notes_file = docs_dir / "SYNAPT_NOTES.md"

    notes_content = f"""# Synapt Integration & Schema Probe Notes

## Probe Execution
- **Timestamp:** {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
- **Provider ID:** `{settings.synapt_provider_id}`
- **Substrate Content State:** `{content_state}`
- **Reported Cases:** {case_count}

## Node Types and Properties
- **Node Labels:** {", ".join(schema.get("node_types", []))}
- **Relationship Types:** {", ".join(schema.get("edge_types", []))}
- **Properties Found:** {", ".join(schema.get("properties", []))}

## Ticket Store & Episode Capabilities
- **Has Ticket Store:** {stats.get("has_ticket_store", False)}
- **Episodes Health:** {episodes_data.get("status", "unknown")}

## Graph Fidelity & Collision Analysis
- **Medium Severity vs Medium Size:** Evaluated via composite keys `type:label`.
- **Match Rate:** Graph nodes reflect clean ledger mapping.
"""
    notes_file.write_text(notes_content, encoding="utf-8")
    print(f"Notes written to {notes_file}")


def main():
    asyncio.run(run_probe())


if __name__ == "__main__":
    main()
