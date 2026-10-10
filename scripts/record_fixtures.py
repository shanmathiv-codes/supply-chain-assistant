"""Record substrate tool responses to fixtures directory for replay mode."""
import asyncio
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.substrate.gateway import SynaptReadGateway


async def record(prefer_mode: str = "mock"):
    fixtures_dir = ROOT_DIR / "fixtures" / "synapt" / "real"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    try:
        gw = SynaptReadGateway(mode=prefer_mode)
        stats = await gw.get_stats()
    except Exception:
        gw = SynaptReadGateway(mode="mock")
        stats = await gw.get_stats()
    s_dir = fixtures_dir / "trident_get_stats"
    s_dir.mkdir(parents=True, exist_ok=True)
    (s_dir / "default.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    # Record schema
    schema = await gw.get_schema()
    sc_dir = fixtures_dir / "trident_get_schema"
    sc_dir.mkdir(parents=True, exist_ok=True)
    (sc_dir / "default.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    # Record sample query
    q_res = await gw.query("Natural disaster in automotive Tier 1 supplier")
    q_dir = fixtures_dir / "trident_query"
    q_dir.mkdir(parents=True, exist_ok=True)
    (q_dir / "default.json").write_text(
        json.dumps({k: v for k, v in q_res.items() if k != "evidence"}, indent=2), encoding="utf-8"
    )

    print(f"Recorded fixtures saved in {fixtures_dir}")


if __name__ == "__main__":
    asyncio.run(record())
