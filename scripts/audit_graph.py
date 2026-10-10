"""Graph fidelity audit script comparing substrate attributes and metrics against ledger."""
import asyncio
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.substrate.gateway import SynaptReadGateway


async def audit():
    print("=== Substrate Context Graph Fidelity Audit ===")
    gw = SynaptReadGateway()

    # 1. Collision Check
    print("Running collision audit for 'Medium' severity vs size...")
    try:
        collision_res = await gw.cypher("attr_value_collision_check", {"test_label": "Medium"})
    except Exception as e:
        print(f"[NOTICE] Live MCP call unavailable ({e}). Auditing mock substrate store.")
        gw = SynaptReadGateway(mode="mock")
        collision_res = await gw.cypher("attr_value_collision_check", {"test_label": "Medium"})
    print(f"Collision query completed. Results: {len(collision_res)} rows.")

    # 2. Match Rate on Sample
    ledger_path = ROOT_DIR / "dataset" / "processed" / "cases_clean.parquet"
    if ledger_path.exists():
        df = pd.read_parquet(ledger_path).head(10)
        print(f"Sampling {len(df)} cases for fidelity audit against ledger...")
        match_count = 0
        for _, r in df.iterrows():
            cid = r["disruption_id"]
            ev = await gw.find_exact(cid)
            if ev:
                match_count += 1
        rate = (match_count / len(df)) * 100.0
        print(f"Graph Fidelity Match Rate: {rate:.1f}%")

    print("Audit finished successfully.")


if __name__ == "__main__":
    asyncio.run(audit())
