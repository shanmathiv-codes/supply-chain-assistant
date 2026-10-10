"""Unit tests for the LLM layer: FakeLLM, router, cache, limiter, structured parser."""
import pytest
from pydantic import BaseModel

from app.llm.cache import LLMCache
from app.llm.fake import fake_llm
from app.llm.limiter import ConcurrencyController, ProviderRateLimiter
from app.llm.router import LLMRouter
from app.llm.structured import parse_and_validate
from app.workflow.budget import RunBudget


class DummySchema(BaseModel):
    status: str
    code: int


def test_fake_llm_all_prompts():
    """Verify that FakeLLM produces valid structured outputs across all prompt roles."""
    ctx = {
        "text": "Critical natural disaster flood at Tier 1 automotive plant in North America.",
        "disruption_type": "Natural Disaster",
        "disruption_severity": "Critical",
        "evidence_ids": ["EV-101", "EV-102"],
    }

    # Intake
    res_intake = fake_llm.invoke("intake", ctx)
    assert res_intake["disruption_type"] == "Natural Disaster"
    assert res_intake["disruption_severity"] == "Critical"
    assert "missing_fields" in res_intake

    # Classify
    res_classify = fake_llm.invoke("classify", ctx)
    assert res_classify["disruption_type"] == "Natural Disaster"
    assert res_classify["confidence"] > 0.0

    # Response Plan
    res_plan = fake_llm.invoke("response_plan", ctx)
    assert "recommendations" in res_plan
    assert len(res_plan["recommendations"]) > 0
    assert res_plan["recommendations"][0]["evidence_ids"]

    # Recovery
    res_rec = fake_llm.invoke("recovery", ctx)
    assert "key_milestones_days" in res_rec
    assert "full_recovery" in res_rec["key_milestones_days"]

    # Synthesize
    res_syn = fake_llm.invoke("synthesize", ctx)
    assert "claims" in res_syn
    assert any(c["kind"] == "HISTORICAL_FACT" for c in res_syn["claims"])

    # Judge
    res_judge = fake_llm.invoke("judge", ctx)
    assert res_judge["passed"] is True
    assert "relevance" in res_judge["scores"]


def test_llm_cache(tmp_path):
    """Test LLM cache insertion, lookup, and hash stability."""
    db_file = tmp_path / "test_cache.db"
    cache = LLMCache(db_file)

    messages = [{"role": "user", "content": "Hello"}]
    data = {"result": "success"}

    # Miss
    assert cache.get("fast", "model-a", "prompt-1", messages, 0.0) is None

    # Put and Hit
    cache.put("fast", "model-a", "prompt-1", messages, 0.0, data, tokens_used=42)
    cached = cache.get("fast", "model-a", "prompt-1", messages, 0.0)
    assert cached == data

    # Different temperature should miss
    assert cache.get("fast", "model-a", "prompt-1", messages, 0.7) is None


@pytest.mark.asyncio
async def test_rate_limiter():
    """Test token bucket rate limiter acquire and concurrency controller."""
    limiter = ProviderRateLimiter("gemini")
    await limiter.acquire()
    assert limiter._daily_count >= 1

    controller = ConcurrencyController(max_concurrent=2)
    async with controller:
        assert True


def test_structured_parsing():
    """Test JSON extraction from clean text, code blocks, and markdown noise."""
    # 1. Clean JSON
    raw1 = '{"status": "ok", "code": 200}'
    data1, model1 = parse_and_validate(raw1, DummySchema)
    assert data1["status"] == "ok"
    assert model1.code == 200

    # 2. Markdown fenced block
    raw2 = 'Here is the output:\n```json\n{"status": "warning", "code": 404}\n```\nHope it helps.'
    data2, model2 = parse_and_validate(raw2, DummySchema)
    assert data2["status"] == "warning"
    assert model2.code == 404

    # 3. Invalid JSON raises ValueError
    with pytest.raises(ValueError):
        parse_and_validate("Not a JSON object at all", DummySchema)


@pytest.mark.asyncio
async def test_router_fake_mode_with_budget():
    """Verify router executes in fake mode without external API calls and tracks budget."""
    router = LLMRouter()
    budget = RunBudget(max_calls=5, max_tokens=1000)

    res_dict, _ = await router.complete_structured(
        prompt_name="intake",
        role="fast",
        messages=[{"role": "user", "content": "Incident at factory"}],
        schema_cls=None,
        context={"text": "Incident at factory"},
        budget=budget,
    )

    assert "disruption_type" in res_dict
    assert budget.calls_made == 1
    assert budget.tokens_used > 0
