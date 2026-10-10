import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

import asyncio
from pathlib import Path
from typing import Any, Literal, Type, TypeVar

from pydantic import BaseModel

from app.core.config import load_yaml_config, settings
from app.core.logging import logger
from app.llm.cache import llm_cache
from app.llm.fake import fake_llm
from app.llm.limiter import concurrency_controller, gemini_limiter, openrouter_limiter
from app.llm.structured import parse_and_validate
from app.workflow.budget import RunBudget

T = TypeVar("T", bound=BaseModel)
MODELS_CONFIG = load_yaml_config("models.yaml")
RESOLVED_PATH = Path("config/models.resolved.yaml")
if RESOLVED_PATH.exists():
    RESOLVED_CONFIG = load_yaml_config("models.resolved.yaml")
else:
    RESOLVED_CONFIG = MODELS_CONFIG


class LLMRouter:
    """Orchestrates model selection, caching, rate limits, repair, and fallback."""

    def __init__(self):
        self.mode = settings.effective_llm_mode

    def _get_candidates_for_role(self, role: str) -> list[str]:
        role_cfg = RESOLVED_CONFIG.get("roles", {}).get(role, {})
        return list(role_cfg.get("candidates", []))

    async def complete_structured(
        self,
        prompt_name: str,
        role: Literal["fast", "reason", "judge"],
        messages: list[dict[str, str]],
        schema_cls: Type[T] | None = None,
        context: dict[str, Any] | None = None,
        budget: RunBudget | None = None,
    ) -> tuple[dict[str, Any], T | None]:
        """Execute prompt and return structured JSON dictionary and validated model."""
        ctx = context or {}

        # 1. Fake Mode dispatch
        if self.mode == "fake":
            res_dict = fake_llm.invoke(prompt_name, ctx)
            validated = schema_cls.model_validate(res_dict) if schema_cls else None
            if budget:
                budget.record_usage(calls=1, tokens=150)
            return res_dict, validated

        candidates = self._get_candidates_for_role(role)
        temperature = MODELS_CONFIG.get("roles", {}).get(role, {}).get("temperature", 0.0)

        # 2. Check Cache
        for cand in candidates:
            cached = llm_cache.get(role, cand, prompt_name, messages, temperature)
            if cached:
                validated = schema_cls.model_validate(cached) if schema_cls else None
                return cached, validated

        if self.mode == "cache":
            raise RuntimeError(
                f"LLM_MODE is 'cache' but prompt '{prompt_name}' ({role}) has no cached response."
            )

        # 3. Live Mode execution with candidate fallback
        for cand in candidates:
            provider = "gemini" if "gemini" in cand else "openrouter"
            limiter = gemini_limiter if provider == "gemini" else openrouter_limiter

            try:
                async with concurrency_controller:
                    await limiter.acquire()

                    import litellm
                    litellm.telemetry = False

                    # Prepare provider kwargs
                    extra_kwargs = {}
                    if provider == "gemini":
                        key = settings.get_effective_gemini_key()
                        if key:
                            extra_kwargs["api_key"] = key
                    elif provider == "openrouter":
                        if settings.openrouter_api_key:
                            extra_kwargs["api_key"] = settings.openrouter_api_key
                        extra_kwargs["extra_headers"] = {
                            "HTTP-Referer": settings.openrouter_site_url,
                            "X-Title": settings.openrouter_app_name,
                        }

                    litellm.request_timeout = 30.0
                    resp = await asyncio.wait_for(
                        litellm.acompletion(
                            model=cand,
                            messages=messages,
                            temperature=temperature,
                            request_timeout=30.0,
                            **extra_kwargs,
                        ),
                        timeout=30.0,
                    )

                    raw_content = resp.choices[0].message.content
                    tokens = resp.usage.total_tokens if hasattr(resp, "usage") and resp.usage else 250
                    if budget:
                        budget.record_usage(calls=1, tokens=tokens)

                    # Extract and validate
                    try:
                        data, validated = parse_and_validate(raw_content, schema_cls)
                        llm_cache.put(role, cand, prompt_name, messages, temperature, data, tokens)
                        return data, validated
                    except Exception as parse_err:
                        logger.warning(f"Initial JSON parse failed for {cand}: {parse_err}. Attempting 1 repair.")
                        # Attempt single-retry repair
                        repair_messages = list(messages) + [
                            {"role": "assistant", "content": raw_content},
                            {
                                "role": "user",
                                "content": f"The response was not valid JSON conforming to schema: {parse_err}. Fix and return ONLY valid JSON.",
                            },
                        ]
                        repair_resp = await asyncio.wait_for(
                            litellm.acompletion(
                                model=cand,
                                messages=repair_messages,
                                temperature=0.0,
                                request_timeout=20.0,
                                **extra_kwargs,
                            ),
                            timeout=20.0,
                        )
                        repair_content = repair_resp.choices[0].message.content
                        data, validated = parse_and_validate(repair_content, schema_cls)
                        llm_cache.put(role, cand, prompt_name, messages, temperature, data, tokens + 100)
                        return data, validated

            except Exception as exc:
                logger.warning(f"Candidate model {cand} failed: {exc}. Trying next candidate.")
                continue

        logger.error(f"All live candidates exhausted for role {role}. Falling back to FakeLLM.")
        res_dict = fake_llm.invoke(prompt_name, ctx)
        validated = schema_cls.model_validate(res_dict) if schema_cls else None
        return res_dict, validated


router = LLMRouter()
