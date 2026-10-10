"""Contract tests verifying SynaptReadGateway across mock and replay modes."""

import pytest

from app.schemas.evidence import SubstrateCall
from app.substrate.gateway import SynaptReadGateway


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["mock", "replay"])
async def test_read_gateway_contract(mode):
    # If replay fixtures not recorded yet, record them first
    if mode == "replay":
        from scripts.record_fixtures import record

        await record()

    gw = SynaptReadGateway(mode=mode)
    trace = []

    # 1. Health
    h = await gw.health()
    assert h["status"] == "ok"

    # 2. Stats
    stats = await gw.get_stats(trace=trace)
    assert isinstance(stats, dict)
    assert len(trace) >= 1
    assert isinstance(trace[-1], SubstrateCall)
    assert trace[-1].ok

    # 3. Schema
    schema = await gw.get_schema(trace=trace)
    assert "node_types" in schema

    # 4. Query
    q_res = await gw.query("Natural disaster in automotive Tier 1 supplier", top_k=3, trace=trace)
    assert "answer" in q_res
    assert "confidence" in q_res

    # 5. Exact match (mock mode)
    if mode == "mock":
        exact_res = await gw.find_exact("DIS-00001", trace=trace)
        assert isinstance(exact_res, list)
        if exact_res:
            assert exact_res[0].provenance_mode == "MOCK"
