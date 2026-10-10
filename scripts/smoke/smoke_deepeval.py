"""Smoke test for DeepEval imports."""

try:
    import deepeval
    from deepeval.test_case import LLMTestCase

    _ = LLMTestCase
    print(f"DeepEval smoke test passed: version {getattr(deepeval, '__version__', 'available')}")
except ImportError as e:
    print(f"DeepEval not installed in this environment (expected if in .venv vs .venv-eval): {e}")

if __name__ == "__main__":
    pass
