"""Authentication client for Synapt S2S registered agent flow and session token management."""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


class TokenError(RuntimeError):
    """The token endpoint failed or credentials are missing."""


def decode_exp(token: str) -> float:
    """Read `exp` claim out of a JWT without verifying signature."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return float(data.get("exp", 0))
    except Exception:
        return 0.0


class StaticTokenSource:
    """Session token pasted directly from environment."""

    def __init__(self, token: str, client_id: str = "(static token)") -> None:
        if not token:
            raise TokenError("StaticTokenSource requires a non-empty token")
        self.client_id = client_id
        self.scope: Any = None
        self._token = token

    async def token(self, *, force: bool = False) -> str:
        if force:
            raise TokenError(
                "Static session token expired or rejected and cannot be auto-refreshed."
            )
        return self._token


class SecretTokenSource:
    """Registered-agent flow: exchange client_id + client_secret for a session token."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        verify: bool | str = True,
        timeout: float = 30.0,
    ) -> None:
        if not (token_url and client_id and client_secret):
            raise TokenError("token_url, client_id and client_secret are all required")
        self.token_url = token_url
        self.client_id = client_id
        self._secret = client_secret
        self._verify = verify
        self._timeout = timeout
        self._token: str | None = None
        self._expiry = 0.0
        self.scope: list[str] | None = None

    async def token(self, *, force: bool = False) -> str:
        now = time.time()
        if not force and self._token and now < (self._expiry - 30.0):
            return self._token

        async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify) as http:
            resp = await http.post(
                self.token_url,
                json={"client_id": self.client_id, "client_secret": self._secret},
            )

        if resp.status_code == 401:
            raise TokenError(
                f"/generate_token returned 401 for client {self.client_id!r}: "
                f"credentials invalid or revoked. Server said: {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise TokenError(
                f"/generate_token failed ({resp.status_code}) at {self.token_url} for "
                f"client {self.client_id!r}: {resp.text[:300]}"
            )

        data: dict[str, Any] = resp.json()
        tok = data.get("token") or data.get("access_token")
        if not tok:
            raise TokenError(f"Token endpoint returned no token; response keys={list(data.keys())}")

        self._token = tok
        self.scope = data.get("scope")
        self._expiry = self._parse_expiry(data) or (decode_exp(tok) or now + 900.0)
        return tok

    @staticmethod
    def _parse_expiry(data: dict[str, Any]) -> float:
        raw = data.get("expires_at")
        if not raw:
            ttl = data.get("expires_in")
            return time.time() + float(ttl) if ttl else 0.0
        try:
            clean_iso = str(raw).replace("Z", "+00:00")
            return datetime.fromisoformat(clean_iso).timestamp()
        except (ValueError, TypeError):
            return 0.0


class SynaptAuthClient:
    """Manages token retrieval, S2S registered agent flow, and automatic renewal."""

    def __init__(self):
        self._source: SecretTokenSource | StaticTokenSource | None = None
        self._cached_token: str | None = None
        self._token_expiry_ts: float = 0.0
        self.scope: list[str] | None = None

    def _get_or_create_source(self) -> SecretTokenSource | StaticTokenSource | None:
        if settings.synapt_agent_token and settings.synapt_agent_token.strip():
            return StaticTokenSource(settings.synapt_agent_token.strip())

        client_id = settings.synapt_agent_client_id
        client_secret = settings.synapt_agent_client_secret
        if client_id and client_id.strip() and client_secret and client_secret.strip():
            return SecretTokenSource(
                token_url=settings.effective_synapt_token_url,
                client_id=client_id.strip(),
                client_secret=client_secret.strip(),
                verify=settings.effective_synapt_verify,
                timeout=min(settings.synapt_query_timeout, 30.0),
            )
        return None

    @property
    def auth_mode(self) -> str:
        if settings.synapt_agent_token and settings.synapt_agent_token.strip():
            return "static"
        if (
            settings.synapt_agent_client_id
            and settings.synapt_agent_client_id.strip()
            and settings.synapt_agent_client_secret
        ):
            return "secret"
        if settings.synapt_username and settings.synapt_password:
            return "legacy"
        return "none"

    @property
    def client_id(self) -> str:
        if self.auth_mode == "secret":
            return settings.synapt_agent_client_id or ""
        if self.auth_mode == "static":
            return "(static token)"
        return settings.synapt_username or ""

    async def get_token(self, force_refresh: bool = False) -> str | None:
        """Retrieve active Bearer token via S2S registered agent flow or legacy fallback."""
        source = self._get_or_create_source()
        if source is not None:
            try:
                tok = await source.token(force=force_refresh)
                self.scope = getattr(source, "scope", None)
                self._cached_token = tok
                return tok
            except Exception as exc:
                logger.warning(f"S2S token acquisition failed: {exc}")
                raise

        # Legacy fallback if username & password configured
        if settings.synapt_username and settings.synapt_password:
            now = time.time()
            if not force_refresh and self._cached_token and now < (self._token_expiry_ts - 30.0):
                return self._cached_token

            tok_info = await self._authenticate_legacy()
            if tok_info and "token" in tok_info:
                self._cached_token = tok_info["token"]
                expires_in = tok_info.get("expires_in", 3600)
                self._token_expiry_ts = now + float(expires_in)
                return self._cached_token

        return None

    async def _authenticate_legacy(self) -> dict[str, Any] | None:
        """Legacy fallback: authenticate with username / password."""
        auth_url = settings.synapt_auth_base
        username = settings.synapt_username
        password = settings.synapt_password
        verify = settings.effective_synapt_verify

        async with httpx.AsyncClient(timeout=15.0, verify=verify) as client:
            try:
                resp = await client.post(
                    auth_url,
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("access_token") or data.get("token")
                    if tok:
                        return {"token": tok, "expires_in": data.get("expires_in", 3600)}
            except Exception:
                pass
        return None


synapt_auth_client = SynaptAuthClient()
