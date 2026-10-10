"""Application configuration with Pydantic v2 settings, YAML loaders, and mode banner."""
import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Disable LiteLLM external lookups
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"


def load_yaml_config(file_name: str) -> dict[str, Any]:
    """Safely load a YAML configuration file from config/ directory."""
    path = CONFIG_DIR / file_name
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class Settings(BaseSettings):
    """Global configuration settings resolved from environment variables and defaults."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Settings
    llm_mode: Literal["live", "cache", "fake"] = Field(default="fake", alias="LLM_MODE")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_site_url: str = Field(default="http://localhost", alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="scd-assistant", alias="OPENROUTER_APP_NAME")

    # Synapt Substrate Settings
    synapt_mode: Literal["auto", "mcp", "replay", "mock"] = Field(default="auto", alias="SYNAPT_MODE")
    synapt_mcp_url: str = Field(default="https://beta.synapt.ai/tristore/mcp/", alias="SYNAPT_MCP_URL")
    synapt_auth_base: str = Field(default="https://beta.synapt.ai/auth_service/api/v1/auth/token", alias="SYNAPT_AUTH_BASE")
    synapt_username: str | None = Field(default=None, alias="SYNAPT_USERNAME")
    synapt_password: str | None = Field(default=None, alias="SYNAPT_PASSWORD")
    synapt_provider_id: str | None = Field(default=None, alias="SYNAPT_PROVIDER_ID")
    synapt_provider_eval_id: str | None = Field(default=None, alias="SYNAPT_PROVIDER_EVAL_ID")
    synapt_top_k: int = Field(default=5, alias="SYNAPT_TOP_K")
    synapt_graph_hops: int = Field(default=2, alias="SYNAPT_GRAPH_HOPS")
    synapt_mcp_transport: Literal["auto", "streamable_http", "sse"] = Field(default="auto", alias="SYNAPT_MCP_TRANSPORT")
    ingestion_state: Literal["agent_prepared", "user_preingested", "schema_only"] = Field(
        default="user_preingested", alias="INGESTION_STATE"
    )
    synapt_sample_size: int = Field(default=500, alias="SYNAPT_SAMPLE_SIZE")
    synapt_sample_format: Literal["cards", "csv"] = Field(default="cards", alias="SYNAPT_SAMPLE_FORMAT")

    # Service & API
    api_key: str | None = Field(default=None, alias="API_KEY")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_base_url: str = Field(default="http://127.0.0.1:8000", alias="API_BASE_URL")

    # Dataset
    dataset_source: Literal["auto", "real", "synthetic"] = Field(default="auto", alias="DATASET_SOURCE")
    kaggle_username: str | None = Field(default=None, alias="KAGGLE_USERNAME")
    kaggle_key: str | None = Field(default=None, alias="KAGGLE_KEY")
    dataset_kaggle_slug: str = Field(
        default="likithagedipudi/supply-chain-disruption-and-recovery-dataset",
        alias="DATASET_KAGGLE_SLUG",
    )

    def get_effective_gemini_key(self) -> str | None:
        key = self.gemini_api_key or self.google_api_key
        return key.strip() if key and key.strip() else None

    @property
    def effective_synapt_mode(self) -> Literal["mcp", "replay", "mock"]:
        """Resolve auto mode based on credential and configuration completeness."""
        if self.synapt_mode == "auto":
            has_creds = bool(
                self.synapt_mcp_url
                and self.synapt_username
                and self.synapt_username.strip()
                and self.synapt_password
                and self.synapt_password.strip()
                and self.synapt_provider_id
                and self.synapt_provider_id.strip()
            )
            return "mcp" if has_creds else "mock"
        if self.synapt_mode in ("mcp", "replay", "mock"):
            return self.synapt_mode  # type: ignore
        return "mock"

    @property
    def effective_llm_mode(self) -> Literal["live", "cache", "fake"]:
        """Resolve LLM mode; gracefully degrades to fake if live requested without keys."""
        if self.llm_mode == "live":
            or_key = self.openrouter_api_key.strip() if self.openrouter_api_key else None
            has_keys = bool(self.get_effective_gemini_key() or or_key)
            return "live" if has_keys else "fake"
        return self.llm_mode

    @property
    def runtime_modes(self) -> dict[str, str]:
        """Dictionary of resolved runtime operational modes."""
        return {
            "llm_mode": self.effective_llm_mode,
            "synapt_mode": self.effective_synapt_mode,
            "dataset_source": self.dataset_source,
            "ingestion_state": self.ingestion_state,
        }

    def startup_banner(self) -> str:
        """Render a clean startup banner with active runtime modes."""
        modes = self.runtime_modes
        lines = [
            "============================================================",
            "  AI-POWERED SUPPLY CHAIN DISRUPTION ASSISTANT              ",
            "============================================================",
            f"  LLM Mode        : {modes['llm_mode'].upper()}",
            f"  Synapt Mode     : {modes['synapt_mode'].upper()}",
            f"  Dataset Source  : {modes['dataset_source'].upper()}",
            f"  Ingestion State : {modes['ingestion_state'].upper()}",
            f"  API Endpoint    : {self.api_base_url}",
        ]
        if modes["synapt_mode"] == "mock":
            lines.append("  [NOTICE] Using MOCK Substrate. Results are simulated.")
        if modes["llm_mode"] == "fake":
            lines.append("  [NOTICE] Using FAKE LLM. Output is deterministic template.")
        lines.append("============================================================")
        return "\n".join(lines)


settings = Settings()
