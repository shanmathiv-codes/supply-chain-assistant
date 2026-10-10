import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

import asyncio
import sys
import time
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import load_yaml_config, settings

MODELS_CONFIG = load_yaml_config("models.yaml")


async def probe_single_model(model_name: str) -> tuple[bool, float]:
    """Send tiny JSON test request to candidate model measuring latency and validity."""
    provider = "gemini" if "gemini" in model_name else "openrouter"
    import litellm

    litellm.telemetry = False

    extra_kwargs = {}
    if provider == "gemini":
        key = settings.get_effective_gemini_key()
        if not key:
            return False, 0.0
        extra_kwargs["api_key"] = key
    elif provider == "openrouter":
        if not settings.openrouter_api_key:
            return False, 0.0
        extra_kwargs["api_key"] = settings.openrouter_api_key
        extra_kwargs["extra_headers"] = {
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
        }

    t0 = time.perf_counter()
    try:
        litellm.request_timeout = 3.0
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model=model_name,
                messages=[{"role": "user", "content": 'Return JSON: {"status": "ok"}'}],
                request_timeout=3.0,
                **extra_kwargs,
            ),
            timeout=3.0,
        )
        latency = (time.perf_counter() - t0) * 1000.0
        content = resp.choices[0].message.content
        ok = "ok" in content.lower()
        return ok, latency
    except Exception:
        return False, 0.0


async def probe_all_models():
    print("=== Probing Free LLM Models ===")
    gemini_key = settings.get_effective_gemini_key()
    openrouter_key = settings.openrouter_api_key

    if not gemini_key and not openrouter_key:
        print(
            "\n[NOTICE] No LLM API keys configured in .env (GEMINI_API_KEY / OPENROUTER_API_KEY).\n"
            "To probe live models, provide keys in .env and re-run: python -m scripts.dev probe-models\n"
            "Using default candidates from config/models.yaml.\n"
        )
        resolved_path = ROOT_DIR / "config" / "models.resolved.yaml"
        resolved_path.write_text(yaml.safe_dump(MODELS_CONFIG), encoding="utf-8")
        print(f"Written default models to {resolved_path}")
        return

    resolved_roles = {}
    for role, spec in MODELS_CONFIG.get("roles", {}).items():
        candidates = spec.get("candidates", [])
        print(f"\nProbing {len(candidates)} candidates for role '{role}' in parallel...")
        results = await asyncio.gather(*[probe_single_model(cand) for cand in candidates])
        working = []
        for cand, (ok, lat) in zip(candidates, results):
            if ok:
                print(f"  {cand}: [OK] ({lat:.0f}ms)")
                working.append(cand)
            else:
                print(f"  {cand}: [FAILED / UNAVAILABLE]")
        resolved_roles[role] = {
            "candidates": working if working else candidates,
            "temperature": spec.get("temperature", 0.0),
            "timeout_seconds": spec.get("timeout_seconds", 30),
        }

    resolved_config = dict(MODELS_CONFIG)
    resolved_config["roles"] = resolved_roles

    resolved_path = ROOT_DIR / "config" / "models.resolved.yaml"
    resolved_path.write_text(yaml.safe_dump(resolved_config), encoding="utf-8")
    print(f"\nResolved models saved to {resolved_path}")


def main():
    asyncio.run(probe_all_models())


if __name__ == "__main__":
    main()
