"""In-memory rate limiter for service API protection."""
import time
from collections import defaultdict


class InMemoryRateLimiter:
    """Simple thread-safe in-memory sliding window rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old timestamps
        timestamps = [ts for ts in self.requests[client_id] if ts > cutoff]
        if len(timestamps) >= self.limit:
            self.requests[client_id] = timestamps
            return False

        timestamps.append(now)
        self.requests[client_id] = timestamps
        return True

    def reset(self):
        self.requests.clear()


service_rate_limiter = InMemoryRateLimiter(requests_per_minute=120)
