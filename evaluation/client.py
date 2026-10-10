"""Lightweight HTTP API client for evaluation harness.

Rule: This module NEVER imports from `app`. It strictly communicates with the
running FastAPI service via HTTP using `httpx`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class EvaluationAPIClient:
    """HTTP Client for interacting with the Supply Chain Disruption API."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> EvaluationAPIClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        """Check API health and runtime modes."""
        resp = self.client.get("/health")
        resp.raise_for_status()
        return resp.json()

    def search(
        self,
        profile: dict[str, Any],
        top_k: int = 5,
        min_cases: int = 3,
        relax_ladder: bool = True,
    ) -> dict[str, Any]:
        """POST /disruptions/search."""
        payload = {
            "profile": profile,
            "top_k": top_k,
            "min_cases": min_cases,
            "relax_ladder": relax_ladder,
        }
        resp = self.client.post("/disruptions/search", json=payload)
        resp.raise_for_status()
        return resp.json()

    def classify(self, request: dict[str, Any]) -> dict[str, Any]:
        """POST /disruptions/classify."""
        resp = self.client.post("/disruptions/classify", json=request)
        resp.raise_for_status()
        return resp.json()

    def prioritize(self, request: dict[str, Any]) -> dict[str, Any]:
        """POST /disruptions/prioritize."""
        resp = self.client.post("/disruptions/prioritize", json=request)
        resp.raise_for_status()
        return resp.json()

    def predict(self, request: dict[str, Any]) -> dict[str, Any]:
        """POST /disruptions/predict."""
        resp = self.client.post("/disruptions/predict", json=request)
        resp.raise_for_status()
        return resp.json()

    def analyze(self, request: dict[str, Any], stream: bool = False) -> dict[str, Any]:
        """POST /disruptions/analyze."""
        url = "/disruptions/analyze"
        if stream:
            url += "?stream=true"
        resp = self.client.post(url, json=request)
        resp.raise_for_status()
        return resp.json()

    def get_run(self, run_id: str) -> dict[str, Any]:
        """GET /runs/{id}."""
        resp = self.client.get(f"/runs/{run_id}")
        resp.raise_for_status()
        return resp.json()

    def get_case(self, case_id: str) -> dict[str, Any]:
        """GET /cases/{case_id}."""
        resp = self.client.get(f"/cases/{case_id}")
        resp.raise_for_status()
        return resp.json()

    def submit_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /feedback."""
        resp = self.client.post("/feedback", json=payload)
        resp.raise_for_status()
        return resp.json()
