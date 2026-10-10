# Architectural and Implementation Decisions

## Decision Log

### DEC-001: Offline Telemetry and Cost-Map Fetch Disabled for LiteLLM
- **Context:** On Windows in restricted / offline / proxy network environments, `import litellm` attempts to download remote model cost tables from GitHub and retries up to 3 times, causing a 15-second hang and SSL certificate warnings.
- **Decision:** Explicitly set `LITELLM_LOCAL_MODEL_COST_MAP=True` and `LITELLM_DISABLE_TELEMETRY=True` across runtime CLI, env check, and app configuration.
- **Alternative Rejected:** Relying on default internet access for library imports; rejected because offline test suites must run without network and without delays.

### DEC-002: Dual Virtual Environment Isolation
- **Context:** DeepEval pulls large dependency graphs (including specific versions of protobuf, openai, typer) that can conflict with LangGraph and LiteLLM runtime versions.
- **Decision:** Maintain separate `.venv` (runtime) and `.venv-eval` (evaluation) virtual environments. The evaluation harness communicates with the runtime microservice exclusively via HTTP and saved JSON run traces.
- **Alternative Rejected:** Single combined virtual environment.

### DEC-003: Permutation Importance Fallback for Explainability
- **Context:** SHAP TreeExplainer requires compiled C-extensions which can encounter platform-specific compilation hurdles or wheel mismatches on some Windows setups.
- **Decision:** Wrap SHAP TreeExplainer calls in try/except with automatic graceful fallback to scikit-learn `permutation_importance`.
- **Alternative Rejected:** Hard dependency failure when SHAP is unavailable.
