"""End-to-End Smoke Test for Supply Chain Disruption Assistant.

Executes a full integration verification:
1. Validates pipeline artifacts and trained models.
2. Starts FastAPI backend on an ephemeral free port in a subprocess.
3. Polls GET /health until ready.
4. Calls POST /disruptions/analyze (Fake LLM + Mock Substrate).
5. Verifies:
   - Report schema contract
   - status in ("ok", "degraded")
   - 100% evidence coverage of historical claims (all cited evidence_ids exist)
   - Limitations disclose active runtime modes (mock/fake/synthetic)
6. Calls POST /disruptions/predict and asserts conformal intervals.
7. Shuts down backend cleanly without orphaned processes.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("scripts.e2e_smoke")

BASE_DIR = Path(__file__).resolve().parent.parent


def find_free_port() -> int:
    """Find an available ephemeral port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_api_ready(base_url: str, timeout: float = 15.0) -> bool:
    """Poll GET /health until the service responds HTTP 200."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_e2e_smoke_test() -> bool:
    """Execute the end-to-end integration test."""
    logger.info("=== Starting E2E Integration Smoke Test ===")

    # 1. Verify filesystem prerequisites
    required_paths = [
        BASE_DIR / "dataset" / "processed" / "cases_clean.parquet",
        BASE_DIR / "dataset" / "splits" / "train.parquet",
        BASE_DIR / "artifacts" / "models" / "production_impact_pct" / "model_card.json",
    ]
    for path in required_paths:
        if not path.exists():
            logger.error("Prerequisite artifact missing: %s", path)
            return False
    logger.info("Artifact prerequisites verified.")

    # 2. Pick port and launch FastAPI in subprocess
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    logger.info("Selected ephemeral port %d. Launching FastAPI backend...", port)

    run_env = os.environ.copy()
    run_env["PYTHONUTF8"] = "1"
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    run_env["LITELLM_DISABLE_TELEMETRY"] = "True"
    run_env["API_PORT"] = str(port)
    run_env["LLM_MODE"] = "fake"
    run_env["SYNAPT_MODE"] = "mock"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(BASE_DIR),
        env=run_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # 3. Wait for /health
        logger.info("Polling %s/health...", base_url)
        if not wait_for_api_ready(base_url, timeout=15.0):
            logger.error("API failed to start within timeout.")
            return False
        logger.info("FastAPI service is HEALTHY and ready.")

        # 4. Test POST /disruptions/analyze
        logger.info("Testing POST /disruptions/analyze with multi-agent workflow...")
        analyze_payload = {
            "profile": {
                "disruption_type": "Port Closure",
                "disruption_severity": "High",
                "industry": "Automotive",
                "supplier_region": "APAC",
                "supplier_tier": "Tier 1",
                "supplier_size": "Large",
                "has_backup_supplier": "Yes",
            },
            "free_text": "Severe typhoon warning closing key maritime hub in East Asia.",
        }

        req = urllib.request.Request(
            f"{base_url}/disruptions/analyze",
            data=json.dumps(analyze_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            assert resp.status == 200, f"Expected HTTP 200, got {resp.status}"
            report: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

        # Assert Report Contract
        assert "run_id" in report, "Missing run_id in report"
        assert report["status"] in ("ok", "degraded"), f"Invalid status: {report.get('status')}"
        logger.info(
            "Report generated successfully (Run ID: %s, Status: %s)",
            report["run_id"],
            report["status"],
        )

        # Assert 100% Evidence Coverage on Historical Facts
        evidence_dict = report.get("evidence", {})
        claims = report.get("claims", [])
        hist_claims = [c for c in claims if c.get("kind") == "HISTORICAL_FACT"]

        logger.info("Verifying evidence coverage on %d historical fact claims...", len(hist_claims))
        for claim in hist_claims:
            ev_ids = claim.get("evidence_ids", [])
            assert len(ev_ids) > 0, f"Claim '{claim.get('text')}' has no evidence citations"
            for eid in ev_ids:
                assert eid in evidence_dict, (
                    f"Evidence ID '{eid}' cited but not present in report evidence"
                )
        logger.info("100% Historical Claim Evidence Grounding ASSERTED!")

        # Assert Limitations mention active runtime modes
        limitations = " ".join(report.get("limitations", [])).lower()
        assert "mock" in limitations or "fake" in limitations or "synthetic" in limitations, (
            "Limitations must explicitly disclose active mock/fake/synthetic runtime modes"
        )
        logger.info("Runtime mode limitations disclosure ASSERTED!")

        # 5. Test POST /disruptions/predict
        logger.info("Testing POST /disruptions/predict...")
        predict_payload = {
            "profile": {
                "disruption_type": "Port Closure",
                "industry": "Automotive",
                "supplier_region": "APAC",
                "supplier_tier": "Tier 1",
                "supplier_size": "Large",
                "has_backup_supplier": "Yes",
            }
        }
        req_pred = urllib.request.Request(
            f"{base_url}/disruptions/predict",
            data=json.dumps(predict_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_pred, timeout=10.0) as resp:
            assert resp.status == 200
            pred_res: dict[str, Any] = json.loads(resp.read().decode("utf-8"))

        assert "predictions" in pred_res
        assert len(pred_res["predictions"]) >= 3
        for p in pred_res["predictions"]:
            assert p["low"] <= p["point"] <= p["high"], f"Invalid conformal bounds: {p}"
        logger.info("Split-conformal prediction intervals ASSERTED!")

        logger.info("=== ALL E2E SMOKE VERIFICATIONS PASSED ===")
        return True

    finally:
        logger.info("Terminating API process (PID %d)...", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
            logger.info("API subprocess terminated cleanly.")
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.warning("API process killed after timeout.")


def main() -> None:
    success = run_e2e_smoke_test()
    if not success:
        sys.exit(1)
    print("\nSUCCESS: End-to-end smoke test passed completely.")


if __name__ == "__main__":
    main()
