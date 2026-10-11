"""Unit tests for configuration loading and mode resolution."""

from app.core.config import Settings, settings


def test_settings_default_modes():
    """Settings should default to safe modes without crashing."""
    assert settings.llm_mode in ("live", "cache", "fake")
    assert settings.synapt_mode in ("auto", "mcp", "replay", "mock")
    assert isinstance(settings.runtime_modes, dict)
    assert "llm_mode" in settings.runtime_modes
    assert "synapt_mode" in settings.runtime_modes


def test_settings_missing_keys_never_crash():
    """Initializing Settings with empty environment should never crash."""
    empty_settings = Settings(
        _env_file=None,
        GEMINI_API_KEY="",
        GOOGLE_API_KEY="",
        OPENROUTER_API_KEY="",
        SYNAPT_USERNAME="",
        SYNAPT_PASSWORD="",
        SYNAPT_PROVIDER_ID="",
        LLM_MODE="live",
        SYNAPT_MODE="auto",
    )
    # Effective LLM mode should degrade to fake because keys are missing
    assert empty_settings.effective_llm_mode == "fake"
    # Effective Synapt mode should degrade to mock because credentials are missing
    assert empty_settings.effective_synapt_mode == "mock"


def test_startup_banner_contains_modes():
    """Startup banner should include active modes and notices."""
    banner = settings.startup_banner()
    assert "AI-POWERED SUPPLY CHAIN DISRUPTION ASSISTANT" in banner
    assert "LLM Mode" in banner
    assert "Synapt Mode" in banner


def test_settings_registered_agent_mode_resolution():
    """Registered agent credentials should resolve effective mode to mcp."""
    agent_settings = Settings(
        _env_file=None,
        SYNAPT_AGENT_CLIENT_ID="test-client",
        SYNAPT_AGENT_CLIENT_SECRET="test-secret",
        SYNAPT_PROVIDER_ID="test-provider",
        SYNAPT_MODE="auto",
    )
    assert agent_settings.effective_synapt_mode == "mcp"
    assert (
        agent_settings.effective_synapt_token_url == "https://beta.synapt.ai/api/mcp/generate_token"
    )
