"""Cross-platform development and orchestration CLI for Supply Chain Disruption Assistant."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

# Enforce UTF-8 in python subprocesses
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["LITELLM_DISABLE_TELEMETRY"] = "True"

ROOT_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"
    if not VENV_PYTHON.exists():
        VENV_PYTHON = Path(sys.executable)

EVAL_PYTHON = ROOT_DIR / ".venv-eval" / "Scripts" / "python.exe"
if not EVAL_PYTHON.exists():
    EVAL_PYTHON = ROOT_DIR / ".venv-eval" / "bin" / "python"
    if not EVAL_PYTHON.exists():
        EVAL_PYTHON = Path(sys.executable)


def run_cmd(cmd: list[str], cwd: Path = ROOT_DIR, env: dict | None = None) -> int:
    run_env = os.environ.copy()
    run_env["PYTHONUTF8"] = "1"
    run_env["PYTHONIOENCODING"] = "utf-8"
    if env:
        run_env.update(env)
    print(f"--> Running: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd), env=run_env)
    return result.returncode


def cmd_setup(args):
    """Bootstrap environments, install dependencies, and run env_check."""
    print("=== Step 1: Checking Python runtime environment ===")
    ret = run_cmd([str(VENV_PYTHON), "-m", "scripts.env_check"])
    if ret != 0:
        print("Setup: env_check reported failures.")
        return ret
    print("Setup completed successfully.")
    return 0


def cmd_data(args):
    """Run data pipeline: acquire, clean, store, splits, eda, sample, cards, playbooks, manifest."""
    cmd = [
        str(VENV_PYTHON),
        "-m",
        "data_preprocessing.pipeline",
        "--source",
        args.source,
    ]
    if getattr(args, "force", False):
        cmd.append("--force")
    return run_cmd(cmd)


def cmd_sample(args):
    """Run stratified Synapt sample builder."""
    cmd = [
        str(VENV_PYTHON),
        "-m",
        "data_preprocessing.preprocessing.synapt_sample",
        "--size",
        str(args.size),
        "--format",
        args.format,
    ]
    return run_cmd(cmd)


def cmd_train(args):
    """Train ML regression and classification models."""
    cmd = [str(VENV_PYTHON), "-m", "ml.training.train_regressors"]
    if getattr(args, "final", False):
        cmd.append("--final")
    ret = run_cmd(cmd)
    if ret != 0:
        return ret
    cmd_cls = [str(VENV_PYTHON), "-m", "ml.training.train_classifier"]
    return run_cmd(cmd_cls)


def cmd_test(args):
    """Run offline test suite with pytest."""
    pytest_bin = ROOT_DIR / ".venv" / "Scripts" / "pytest.exe"
    if not pytest_bin.exists():
        cmd = [str(VENV_PYTHON), "-m", "pytest"]
    else:
        cmd = [str(pytest_bin)]
    if args.filter:
        cmd.extend(["-k", args.filter])
    if args.path:
        cmd.append(args.path)
    else:
        cmd.extend(["-q", "tests"])
    return run_cmd(cmd)


def cmd_e2e(args):
    """Run end-to-end smoke test (fake LLM + mock substrate)."""
    return run_cmd([str(VENV_PYTHON), "-m", "scripts.e2e_smoke"])


def cmd_api(args):
    """Launch FastAPI application."""
    port = getattr(args, "port", 8000)
    host = getattr(args, "host", "127.0.0.1")
    reload = getattr(args, "reload", False)
    cmd = [
        str(VENV_PYTHON),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        str(host),
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    return run_cmd(cmd)


def cmd_ui(args):
    """Launch Streamlit dashboard."""
    streamlit_bin = ROOT_DIR / ".venv" / "Scripts" / "streamlit.exe"
    if not streamlit_bin.exists():
        cmd = [str(VENV_PYTHON), "-m", "streamlit", "run", "ui/app.py"]
    else:
        cmd = [str(streamlit_bin), "run", "ui/app.py"]
    return run_cmd(cmd)


def cmd_probe_models(args):
    """Probe available Gemini and OpenRouter free models."""
    return run_cmd([str(VENV_PYTHON), "-m", "scripts.probe_models"])


def cmd_synapt_probe(args):
    """Probe Synapt MCP tools, schema, and content state."""
    return run_cmd([str(VENV_PYTHON), "-m", "scripts.synapt_probe"])


def cmd_record_fixtures(args):
    """Record Synapt tool responses as replay fixtures."""
    return run_cmd([str(VENV_PYTHON), "-m", "scripts.record_fixtures"])


def cmd_ingest(args):
    """Run admin tier ingestion to Synapt."""
    cmd = [
        str(VENV_PYTHON),
        "-m",
        "scripts.ingest_to_synapt",
        "--what",
        args.what,
    ]
    if getattr(args, "confirm", False):
        cmd.append("--confirm")
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    if getattr(args, "provider", None):
        cmd.extend(["--provider", args.provider])
    return run_cmd(cmd)


def cmd_warm_cache(args):
    """Pre-warm LLM cache with demo scenarios."""
    return run_cmd([str(VENV_PYTHON), "-m", "scripts.warm_cache"])


def cmd_eval(args):
    """Run DeepEval and ablation evaluation harness."""
    cmd = [
        str(EVAL_PYTHON),
        "-m",
        "evaluation.report",
        "--budget",
        args.budget,
    ]
    return run_cmd(cmd)


def main():
    parser = argparse.ArgumentParser(
        prog="python -m scripts.dev",
        description="Supply Chain Disruption Assistant Developer CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # setup
    p_setup = subparsers.add_parser("setup", help="Verify dependencies and setup environment")
    p_setup.set_defaults(func=cmd_setup)

    # data
    p_data = subparsers.add_parser("data", help="Execute complete data pipeline")
    p_data.add_argument(
        "--source",
        choices=["auto", "real", "synthetic"],
        default="auto",
        help="Dataset source mode",
    )
    p_data.add_argument("--force", action="store_true", help="Force recomputation of splits")
    p_data.set_defaults(func=cmd_data)

    # sample
    p_sample = subparsers.add_parser("sample", help="Build Synapt stratified sample")
    p_sample.add_argument("--size", type=int, default=500, help="Sample size count")
    p_sample.add_argument(
        "--format", choices=["cards", "csv"], default="cards", help="Sample batch format"
    )
    p_sample.set_defaults(func=cmd_sample)

    # train
    p_train = subparsers.add_parser("train", help="Train ML models")
    p_train.add_argument("--final", action="store_true", help="Evaluate on test split")
    p_train.set_defaults(func=cmd_train)

    # test
    p_test = subparsers.add_parser("test", help="Run offline pytest suite")
    p_test.add_argument("-k", "--filter", help="Test filter expression")
    p_test.add_argument("path", nargs="?", help="Specific test path")
    p_test.set_defaults(func=cmd_test)

    # e2e
    p_e2e = subparsers.add_parser("e2e", help="Run end-to-end smoke test")
    p_e2e.set_defaults(func=cmd_e2e)

    # api
    p_api = subparsers.add_parser("api", help="Start FastAPI service")
    p_api.add_argument("--port", type=int, default=8000, help="Port to listen on")
    p_api.add_argument("--host", default="127.0.0.1", help="Host address")
    p_api.add_argument("--reload", action="store_true", help="Enable reload")
    p_api.set_defaults(func=cmd_api)

    # ui
    p_ui = subparsers.add_parser("ui", help="Start Streamlit UI")
    p_ui.set_defaults(func=cmd_ui)

    # probe-models
    p_pm = subparsers.add_parser("probe-models", help="Probe LLM endpoints and rate limits")
    p_pm.set_defaults(func=cmd_probe_models)

    # synapt-probe
    p_sp = subparsers.add_parser("synapt-probe", help="Probe Synapt MCP tools and provider state")
    p_sp.set_defaults(func=cmd_synapt_probe)

    # record-fixtures
    p_rf = subparsers.add_parser("record-fixtures", help="Record Synapt tool fixtures for replay")
    p_rf.set_defaults(func=cmd_record_fixtures)

    # ingest
    p_ing = subparsers.add_parser("ingest", help="Ingest data to Synapt (admin tier)")
    p_ing.add_argument(
        "--what",
        choices=["cards", "playbooks", "queue"],
        default="cards",
        help="What artifact to ingest",
    )
    p_ing.add_argument("--provider", help="Target Synapt provider ID")
    p_ing.add_argument("--dry-run", action="store_true", default=True, help="Simulate ingestion")
    p_ing.add_argument("--confirm", action="store_true", help="Confirm real ingestion")
    p_ing.set_defaults(func=cmd_ingest)

    # warm-cache
    p_wc = subparsers.add_parser("warm-cache", help="Pre-warm LLM response cache")
    p_wc.set_defaults(func=cmd_warm_cache)

    # eval
    p_ev = subparsers.add_parser("eval", help="Run DeepEval and ablation benchmarks")
    p_ev.add_argument(
        "--budget",
        choices=["small", "medium", "full"],
        default="small",
        help="Evaluation budget",
    )
    p_ev.set_defaults(func=cmd_eval)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
