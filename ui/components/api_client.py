"""Streamlit UI API Client.

Communicates with the FastAPI backend and handles offline/degraded states gracefully.
"""

from __future__ import annotations

import os
from typing import Any

import requests


class UIAPIClient:
    """HTTP Client for Streamlit UI to connect with FastAPI backend."""

    def __init__(self, base_url: str | None = None, timeout: float = 25.0) -> None:
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout

    def check_health(self) -> dict[str, Any]:
        """Check API health and retrieve runtime modes."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "degraded", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def analyze_disruption(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call POST /disruptions/analyze."""
        try:
            resp = requests.post(
                f"{self.base_url}/disruptions/analyze",
                json=payload,
                timeout=self.timeout * 2,
            )
            if resp.status_code == 200:
                return resp.json()
            err_data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            return {
                "status": "error",
                "error_code": err_data.get("detail", {}).get("code", f"HTTP_{resp.status_code}"),
                "message": err_data.get("detail", {}).get("message", resp.text),
            }
        except Exception as e:
            return {"status": "offline", "message": f"Connection error: {e}"}

    def search_similar(self, profile: dict[str, Any], top_k: int = 5) -> dict[str, Any]:
        """Call POST /disruptions/search."""
        try:
            resp = requests.post(
                f"{self.base_url}/disruptions/search",
                json={"profile": profile, "top_k": top_k},
                timeout=self.timeout,
            )
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}

    def prioritize_disruption(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call POST /disruptions/prioritize."""
        try:
            resp = requests.post(
                f"{self.base_url}/disruptions/prioritize",
                json=payload,
                timeout=self.timeout,
            )
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}

    def submit_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call POST /feedback."""
        try:
            resp = requests.post(
                f"{self.base_url}/feedback",
                json=payload,
                timeout=self.timeout,
            )
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}

    def get_evaluations(self) -> dict[str, Any]:
        """Call GET /evaluations."""
        try:
            resp = requests.get(
                f"{self.base_url}/evaluations",
                timeout=self.timeout,
            )
            return resp.json() if resp.status_code == 200 else {"error": resp.text}
        except Exception as e:
            return {"error": str(e)}


api_client = UIAPIClient()
