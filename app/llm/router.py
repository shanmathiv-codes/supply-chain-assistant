import os

import truststore

truststore.inject_into_ssl()

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

import asyncio
from typing import Any, Literal, Type, TypeVar

from pydantic import BaseModel

from app.core.config import CONFIG_DIR, load_yaml_config, settings
from app.core.logging import logger
from app.llm.cache import llm_cache
from app.llm.fake import fake_llm
from app.llm.limiter import concurrency_controller, gemini_limiter, openrouter_limiter
from app.llm.structured import parse_and_validate
from app.workflow.budget import RunBudget

T = TypeVar("T", bound=BaseModel)


def load_runtime_models() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load base models.yaml and resolved models.resolved.yaml, verifying freshness."""
    base_cfg = load_yaml_config("models.yaml")
    resolved_path = CONFIG_DIR / "models.resolved.yaml"
    base_path = CONFIG_DIR / "models.yaml"

    if not resolved_path.exists():
        return base_cfg, base_cfg

    try:
        # If models.resolved.yaml is older than models.yaml, candidates are stale
        if base_path.exists() and resolved_path.stat().st_mtime < base_path.stat().st_mtime:
            logger.info(
                "config/models.resolved.yaml is older than config/models.yaml; ignoring stale resolved configuration."
            )
            return base_cfg, base_cfg
    except Exception:
        pass

    resolved_cfg = load_yaml_config("models.resolved.yaml")
    return base_cfg, resolved_cfg


class LLMRouter:
    """Orchestrates model selection, caching, rate limits, repair, and fallback."""

    def __init__(self):
        self.mode = settings.effective_llm_mode

    def _get_candidates_for_role(self, role: str) -> list[str]:
        base_cfg, resolved_cfg = load_runtime_models()
        configured = base_cfg.get("roles", {}).get(role, {}).get("candidates", [])
        resolved = resolved_cfg.get("roles", {}).get(role, {}).get("candidates", [])

        # Filter resolved candidates so only currently configured candidates are retained
        valid_resolved = [c for c in resolved if c in configured]
        if valid_resolved:
            return valid_resolved

        # Fallback to configured candidates from models.yaml
        return list(configured)

    async def complete_structured(
        self,
        prompt_name: str,
        role: Literal["fast", "reason", "judge"],
        messages: list[dict[str, str]],
        schema_cls: Type[T] | None = None,
        context: dict[str, Any] | None = None,
        budget: RunBudget | None = None,
        fallback_to_fake: bool = True,
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

        base_cfg, _ = load_runtime_models()
        candidates = self._get_candidates_for_role(role)
        role_cfg = base_cfg.get("roles", {}).get(role, {})
        temperature = float(role_cfg.get("temperature", 0.0))
        timeout_seconds = float(role_cfg.get("timeout_seconds", 30))

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

            # Pre-flight check: skip candidates whose provider key is not configured
            if provider == "gemini" and not settings.get_effective_gemini_key():
                logger.debug(f"Candidate {cand} skipped: no Gemini API key configured.")
                continue
            if provider == "openrouter" and not settings.openrouter_api_key:
                logger.debug(f"Candidate {cand} skipped: no OpenRouter API key configured.")
                continue

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

                    litellm.request_timeout = timeout_seconds
                    resp = await asyncio.wait_for(
                        litellm.acompletion(
                            model=cand,
                            messages=messages,
                            temperature=temperature,
                            request_timeout=timeout_seconds,
                            **extra_kwargs,
                        ),
                        timeout=timeout_seconds,
                    )

                    raw_content = resp.choices[0].message.content or ""
                    tokens = (
                        resp.usage.total_tokens if hasattr(resp, "usage") and resp.usage else 250
                    )
                    if budget:
                        budget.record_usage(calls=1, tokens=tokens)

                    # Extract and validate
                    try:
                        data, validated = parse_and_validate(raw_content, schema_cls)
                        llm_cache.put(role, cand, prompt_name, messages, temperature, data, tokens)
                        return data, validated
                    except Exception as parse_err:
                        logger.warning(
                            f"Initial JSON parse failed for {cand}: {parse_err}. Attempting 1 repair."
                        )
                        # Attempt single-retry repair
                        repair_messages = list(messages) + [
                            {"role": "assistant", "content": raw_content},
                            {
                                "role": "user",
                                "content": f"The response was not valid JSON conforming to schema: {parse_err}. Fix and return ONLY valid JSON.",
                            },
                        ]
                        repair_timeout = min(20.0, timeout_seconds)
                        repair_resp = await asyncio.wait_for(
                            litellm.acompletion(
                                model=cand,
                                messages=repair_messages,
                                temperature=0.0,
                                request_timeout=repair_timeout,
                                **extra_kwargs,
                            ),
                            timeout=repair_timeout,
                        )
                        repair_content = repair_resp.choices[0].message.content or ""
                        data, validated = parse_and_validate(repair_content, schema_cls)
                        llm_cache.put(
                            role, cand, prompt_name, messages, temperature, data, tokens + 100
                        )
                        return data, validated

            except Exception as exc:
                clean_err = str(exc)
                gemini_key = settings.get_effective_gemini_key()
                if gemini_key:
                    clean_err = clean_err.replace(gemini_key, "[REDACTED_GEMINI_KEY]")
                if settings.openrouter_api_key:
                    clean_err = clean_err.replace(
                        settings.openrouter_api_key, "[REDACTED_OPENROUTER_KEY]"
                    )
                clean_err = " ".join(clean_err.replace("\n", " ").split())
                if len(clean_err) > 160:
                    clean_err = clean_err[:157] + "..."
                logger.warning(
                    f"Candidate model {cand} failed: {clean_err}. Trying next candidate."
                )
                continue

        if not fallback_to_fake:
            raise RuntimeError(f"All live candidates exhausted for role {role}.")

        logger.error(f"All live candidates exhausted for role {role}. Falling back to FakeLLM.")
        res_dict = fake_llm.invoke(prompt_name, ctx)
        validated = schema_cls.model_validate(res_dict) if schema_cls else None
        return res_dict, validated


router = LLMRouter()
