"""Token-bucket rate limiter with concurrency semaphores and daily quota controls."""
import asyncio
import time

from app.core.config import load_yaml_config

MODELS_CONFIG = load_yaml_config("models.yaml")
RATE_CONFIG = MODELS_CONFIG.get("rate_limits", {})


class ProviderRateLimiter:
    """Token-bucket rate limiter tracking RPM and daily quota per provider."""

    def __init__(self, provider: str):
        self.provider = provider
        spec = RATE_CONFIG.get(provider, {})
        self.rpm = spec.get("requests_per_minute", 15)
        self.daily_quota = spec.get("daily_request_quota", 1000)
        self.interval = 60.0 / max(1, self.rpm)

        self._last_call_time = 0.0
        self._daily_count = 0
        self._day_start = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if needed to respect rate limit, checking daily quota."""
        async with self._lock:
            now = time.time()
            # Reset daily counter every 24 hours
            if now - self._day_start > 86400.0:
                self._day_start = now
                self._daily_count = 0

            if self._daily_count >= self.daily_quota:
                raise RuntimeError(f"Daily quota ({self.daily_quota}) exhausted for {self.provider}.")

            elapsed = now - self._last_call_time
            if elapsed < self.interval:
                sleep_needed = self.interval - elapsed
                await asyncio.sleep(sleep_needed)

            self._last_call_time = time.time()
            self._daily_count += 1


class ConcurrencyController:
    """Global semaphore restricting simultaneous active LLM calls."""

    def __init__(self, max_concurrent: int = 2):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def __aenter__(self):
        await self._semaphore.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._semaphore.release()


concurrency_controller = ConcurrencyController(
    max_concurrent=MODELS_CONFIG.get("concurrency_limit", 2)
)
gemini_limiter = ProviderRateLimiter("gemini")
openrouter_limiter = ProviderRateLimiter("openrouter")
