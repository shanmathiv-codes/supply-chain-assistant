import os

import truststore

truststore.inject_into_ssl()

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import load_yaml_config, settings

PROBE_TIMEOUT = 15.0


def classify_and_sanitize_exception(exc: Exception) -> tuple[str, str]:
    """Categorize failure into distinct failure modes and sanitize secrets."""
    msg = str(exc)
    exc_type = type(exc).__name__

    effective_gemini = settings.get_effective_gemini_key()
    if effective_gemini:
        msg = msg.replace(effective_gemini, "[REDACTED_GEMINI_KEY]")
    if settings.openrouter_api_key:
        msg = msg.replace(settings.openrouter_api_key, "[REDACTED_OPENROUTER_KEY]")

    msg_lower = msg.lower()

    if isinstance(exc, asyncio.TimeoutError) or "timeout" in msg_lower or "timed out" in msg_lower:
        category = "TIMEOUT"
    elif any(
        term in msg_lower
        for term in [
            "401",
            "unauthorized",
            "invalid_api_key",
            "api key not valid",
            "forbidden",
            "403",
        ]
    ):
        category = "AUTHENTICATION_ERROR"
    elif any(
        term in msg_lower
        for term in [
            "404",
            "not found",
            "notfound",
            "no longer available",
            "does not exist",
        ]
    ):
        category = "UNAVAILABLE_MODEL"
    elif any(
        term in msg_lower
        for term in [
            "429",
            "ratelimit",
            "rate limit",
            "quota",
            "resource_exhausted",
        ]
    ):
        category = "RATE_LIMIT_OR_QUOTA"
    elif any(
        term in msg_lower
        for term in [
            "503",
            "unavailable",
            "high demand",
            "overloaded",
        ]
    ):
        category = "SERVICE_UNAVAILABLE"
    elif any(
        term in msg_lower
        for term in [
            "connect",
            "network",
            "connection",
            "socket",
        ]
    ):
        category = "NETWORK_ERROR"
    else:
        category = f"ERROR_{exc_type.upper()}"

    clean_msg = " ".join(msg.replace("\n", " ").split())
    if len(clean_msg) > 160:
        clean_msg = clean_msg[:157] + "..."
    return category, clean_msg


async def probe_single_model(model_name: str) -> tuple[bool, float, str, str]:
    """Send tiny JSON test request to candidate model measuring latency and validity.

    Returns:
        tuple[bool, float, str, str]: (is_success, latency_ms, category, details)
    """
    provider = "gemini" if "gemini" in model_name else "openrouter"
    import litellm

    litellm.telemetry = False

    extra_kwargs: dict[str, Any] = {}
    if provider == "gemini":
        key = settings.get_effective_gemini_key()
        if not key:
            return (
                False,
                0.0,
                "AUTHENTICATION_ERROR",
                "No Gemini API key configured in environment",
            )
        extra_kwargs["api_key"] = key
    elif provider == "openrouter":
        if not settings.openrouter_api_key:
            return (
                False,
                0.0,
                "AUTHENTICATION_ERROR",
                "No OpenRouter API key configured in environment",
            )
        extra_kwargs["api_key"] = settings.openrouter_api_key
        extra_kwargs["extra_headers"] = {
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
        }

    t0 = time.perf_counter()
    try:
        litellm.request_timeout = PROBE_TIMEOUT
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": 'Return a JSON object with: {"status": "ok"}',
                    }
                ],
                request_timeout=PROBE_TIMEOUT,
                **extra_kwargs,
            ),
            timeout=PROBE_TIMEOUT,
        )
        latency = (time.perf_counter() - t0) * 1000.0
        content = resp.choices[0].message.content or ""

        # Validate that response contains valid JSON with status "ok"
        clean_json = content.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.strip("`")
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()

        ok = False
        try:
            parsed = json.loads(clean_json)
            if isinstance(parsed, dict) and str(parsed.get("status", "")).lower() == "ok":
                ok = True
        except Exception:
            if '"status": "ok"' in content.lower() or '{"status":"ok"}' in content.lower():
                ok = True

        if ok:
            return True, latency, "SUCCESS", f"Valid response received in {latency:.0f}ms"
        else:
            return (
                False,
                latency,
                "INVALID_RESPONSE",
                f"Response did not contain valid JSON status 'ok': {content[:80]}",
            )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000.0
        category, details = classify_and_sanitize_exception(exc)
        return False, latency, category, details


async def probe_all_models():
    print("=== Probing Configured LLM Models ===")
    models_config = load_yaml_config("models.yaml")
    gemini_key = settings.get_effective_gemini_key()
    openrouter_key = settings.openrouter_api_key

    if not gemini_key and not openrouter_key:
        print(
            "\n[NOTICE] No LLM API keys configured in .env (GEMINI_API_KEY / OPENROUTER_API_KEY).\n"
            "To probe live models, provide keys in .env and re-run: python -m scripts.dev probe-models\n"
        )
        resolved_roles = {
            role: {
                "candidates": [],
                "temperature": spec.get("temperature", 0.0),
                "timeout_seconds": spec.get("timeout_seconds", 30),
            }
            for role, spec in models_config.get("roles", {}).items()
        }
        resolved_config = dict(models_config)
        resolved_config["roles"] = resolved_roles
        resolved_path = ROOT_DIR / "config" / "models.resolved.yaml"
        resolved_path.write_text(yaml.safe_dump(resolved_config), encoding="utf-8")
        print(f"Written empty resolved candidates to {resolved_path}")
        return

    # Collect unique candidates across all roles
    unique_candidates: list[str] = []
    for _role, spec in models_config.get("roles", {}).items():
        for cand in spec.get("candidates", []):
            if cand not in unique_candidates:
                unique_candidates.append(cand)

    print(
        f"Probing {len(unique_candidates)} unique candidate model(s) (timeout: {PROBE_TIMEOUT}s)..."
    )
    results_map: dict[str, tuple[bool, float, str, str]] = {}
    for cand in unique_candidates:
        print(f"\n--> Probing '{cand}'...")
        ok, lat, category, details = await probe_single_model(cand)
        results_map[cand] = (ok, lat, category, details)
        if ok:
            print(f"    Status: [SUCCESS] ({lat:.0f}ms)")
        else:
            print(f"    Status: [FAILED - {category}] Details: {details}")

    # Build resolved configuration mapping for each role
    print("\n=== Candidate Resolution per Role ===")
    resolved_roles: dict[str, Any] = {}
    for role, spec in models_config.get("roles", {}).items():
        candidates = spec.get("candidates", [])
        working = [cand for cand in candidates if results_map.get(cand, (False,))[0]]
        print(f"\nRole '{role}': {len(working)}/{len(candidates)} candidate(s) operational")
        for cand in candidates:
            ok, lat, cat, _ = results_map.get(cand, (False, 0.0, "UNKNOWN", ""))
            status_str = f"WORKING ({lat:.0f}ms)" if ok else f"FAILED ({cat})"
            print(f"  - {cand}: {status_str}")

        if not working:
            print(f"  [WARNING] No working candidates resolved for role '{role}'.")

        resolved_roles[role] = {
            "candidates": working,
            "temperature": spec.get("temperature", 0.0),
            "timeout_seconds": spec.get("timeout_seconds", 30),
        }

    resolved_config = dict(models_config)
    resolved_config["roles"] = resolved_roles

    resolved_path = ROOT_DIR / "config" / "models.resolved.yaml"
    resolved_path.write_text(yaml.safe_dump(resolved_config), encoding="utf-8")
    print(f"\nResolved models saved to {resolved_path}")


def main():
    asyncio.run(probe_all_models())


if __name__ == "__main__":
    main()
