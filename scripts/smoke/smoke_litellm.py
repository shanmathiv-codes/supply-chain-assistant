"""Smoke test for LiteLLM imports and offline configuration."""

import importlib.metadata
import os

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

import litellm


def run_smoke():
    litellm.telemetry = False
    litellm.drop_params = True
    ver = importlib.metadata.version("litellm")
    print(f"LiteLLM smoke test passed: version {ver}")


if __name__ == "__main__":
    run_smoke()
