"""Authentication client for Synapt token acquisition and memory-only token cache."""
import time
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.core.config import settings

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class SynaptAuthClient:
    """Manages token retrieval, in-memory caching, and automatic renewal."""

    def __init__(self):
        self._cached_token: str | None = None
        self._token_expiry_ts: float = 0.0

    async def get_token(self, force_refresh: bool = False) -> str | None:
        """Retrieve active token, renewing before expiration if needed."""
        now = time.time()
        if not force_refresh and self._cached_token and now < (self._token_expiry_ts - 30.0):
            return self._cached_token

        if not settings.synapt_username or not settings.synapt_password:
            return None

        token_info = await self._authenticate()
        if token_info and "token" in token_info:
            self._cached_token = token_info["token"]
            expires_in = token_info.get("expires_in", 3600)
            self._token_expiry_ts = now + float(expires_in)
            return self._cached_token
        return None

    async def _authenticate(self) -> dict[str, Any] | None:
        """Try OAuth2 form-encoded, JSON body, or Basic auth in sequence."""
        auth_url = settings.synapt_auth_base
        username = settings.synapt_username
        password = settings.synapt_password

        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            # 1. Try OAuth2 form-encoded
            try:
                resp = await client.post(
                    auth_url,
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("access_token") or data.get("token") or (data.get("data", {}).get("access_token"))
                    if tok:
                        self._save_auth_format("form_encoded")
                        return {"token": tok, "expires_in": data.get("expires_in", 3600)}
            except Exception:
                pass

            # 2. Try JSON body
            try:
                resp = await client.post(
                    auth_url,
                    json={"username": username, "password": password},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("access_token") or data.get("token") or (data.get("data", {}).get("access_token"))
                    if tok:
                        self._save_auth_format("json_body")
                        return {"token": tok, "expires_in": data.get("expires_in", 3600)}
            except Exception:
                pass

            # 3. Try HTTP Basic
            try:
                resp = await client.post(auth_url, auth=(username, password))
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("access_token") or data.get("token")
                    if tok:
                        self._save_auth_format("http_basic")
                        return {"token": tok, "expires_in": data.get("expires_in", 3600)}
            except Exception:
                pass

        return None

    def _save_auth_format(self, method: str):
        auth_yaml = CONFIG_DIR / "synapt_auth.yaml"
        spec = {
            "auth_method": method,
            "token_endpoint": settings.synapt_auth_base,
            "tested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "notes": "Verified working authentication method",
        }
        auth_yaml.write_text(yaml.safe_dump(spec), encoding="utf-8")


synapt_auth_client = SynaptAuthClient()
