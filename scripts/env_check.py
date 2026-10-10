"""Environment and dependency verification script."""

import os
import sys

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("httpx", "httpx"),
    ("tenacity", "tenacity"),
    ("yaml", "pyyaml"),
    ("dotenv", "python-dotenv"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("pyarrow", "pyarrow"),
    ("sklearn", "scikit-learn"),
    ("scipy", "scipy"),
    ("shap", "shap"),
    ("joblib", "joblib"),
    ("langgraph", "langgraph"),
    ("langchain_core", "langchain-core"),
    ("litellm", "litellm"),
    ("mcp", "mcp"),
    ("streamlit", "streamlit"),
    ("plotly", "plotly"),
    ("rank_bm25", "rank-bm25"),
    ("pytest", "pytest"),
    ("respx", "respx"),
    ("ruff", "ruff"),
]


def check_env():
    print(f"Python version: {sys.version.split()[0]}", flush=True)
    all_ok = True
    for mod_name, disp_name in PACKAGES:
        try:
            print(f"Checking {disp_name}...", end=" ", flush=True)
            if mod_name == "ruff":
                import ruff

                ver = getattr(ruff, "__version__", "installed")
            else:
                mod = __import__(mod_name)
                ver = getattr(mod, "__version__", "installed")
            print(f"[OK] {ver}", flush=True)
        except Exception as exc:
            all_ok = False
            print(f"[FAIL] {exc}", flush=True)

    if all_ok:
        print("\nAll required dependencies imported successfully.", flush=True)
        return 0
    else:
        print("\nSome dependencies failed to import.", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(check_env())
