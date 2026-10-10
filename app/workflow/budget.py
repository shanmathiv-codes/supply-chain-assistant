"""Run budget tracker ensuring LLM calls and tokens stay within strict limits."""

from app.core.config import load_yaml_config

MODELS_CONFIG = load_yaml_config("models.yaml")
MAX_CALLS_DEFAULT = MODELS_CONFIG.get("budget_max_calls_per_run", 8)
MAX_TOKENS_DEFAULT = MODELS_CONFIG.get("budget_max_tokens_per_run", 16000)


class RunBudget:
    """Tracks LLM invocations and token usage for an individual analysis run."""

    def __init__(self, max_calls: int = MAX_CALLS_DEFAULT, max_tokens: int = MAX_TOKENS_DEFAULT):
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.calls_made = 0
        self.tokens_used = 0

    def record_usage(self, calls: int = 1, tokens: int = 0):
        self.calls_made += calls
        self.tokens_used += tokens
        if self.calls_made > self.max_calls:
            raise RuntimeError(
                f"Run budget exceeded: {self.calls_made} LLM calls made (limit {self.max_calls})"
            )

    @property
    def usage_dict(self) -> dict[str, int]:
        return {
            "calls_made": self.calls_made,
            "max_calls": self.max_calls,
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
        }
