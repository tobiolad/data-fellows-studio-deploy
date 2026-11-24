"""Google OAuth sign-in boundary for Studio.

Google verifies who someone is; it has no notion of Studio's workspace
roles. This module only ever produces a verified (email, name, picture)
identity and a Studio-signed session token carrying whatever global_role
persistence.py has on file for that email (possibly none, i.e. pending).
Nothing here assigns a role: that is an admin action through
PostgresRepository.set_account_role, gated behind STUDIO_GOOGLE_ENABLED so
this whole path is inert until an operator configures real credentials.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt

GOOGLE_ENABLED_ENV = "STUDIO_GOOGLE_ENABLED"
SESSION_TOKEN_TTL_SECONDS = 12 * 60 * 60
_SESSION_TOKEN_PURPOSE = "studio-google-session"


class GoogleAuthError(ValueError):
    """Raised for any invalid Google sign-in exchange or session token."""


@dataclass(frozen=True)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str

    @classmethod
    def from_environment(cls) -> "GoogleOAuthSettings":
        client_id = os.getenv("STUDIO_GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("STUDIO_GOOGLE_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise GoogleAuthError("Studio Google client ID and secret are required")
        return cls(client_id=client_id, client_secret=client_secret)


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    name: str
    picture: str | None


class GoogleOAuthClient:
    """Exchanges an authorization code for a verified Google identity.

    HTTP calls go through small overridable methods so tests can substitute
    a fake transport instead of reaching Google.
    """

    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self, settings: GoogleOAuthSettings, timeout_seconds: float = 5.0) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def exchange(self, code: str, redirect_uri: str) -> GoogleIdentity:
        if not code or len(code) > 4096:
            raise GoogleAuthError("Authorization code is missing or exceeds the size limit")
        token_response = self._post_form(self.token_endpoint, {
            "code": code,
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        access_token = token_response.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise GoogleAuthError("Google did not return an access token")
        user = self._get_json(self.userinfo_endpoint, access_token)
        # Anything but an explicit true is unverified: an unverified address
        # could let whoever holds that Google account sign in as someone else.
        if user.get("verified_email") is not True:
            raise GoogleAuthError("Google has not verified this email address")
        email = user.get("email")
        if not isinstance(email, str) or not email:
            raise GoogleAuthError("Google did not return an email address")
        return GoogleIdentity(email=email, name=user.get("name") or "", picture=user.get("picture"))

    def _post_form(self, url: str, fields: dict[str, str]) -> dict[str, Any]:
        data = urlencode(fields).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        return self._send(request)

    def _get_json(self, url: str, bearer_token: str) -> dict[str, Any]:
        request = Request(url, headers={"Authorization": f"Bearer {bearer_token}"}, method="GET")
        return self._send(request)

    def _send(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise GoogleAuthError("Google returned an error response")
                return json.loads(response.read(64 * 1024).decode("utf-8"))
        except GoogleAuthError:
            raise
        except Exception as exc:
            raise GoogleAuthError("Google could not be reached") from exc


@dataclass(frozen=True)
class SessionPrincipal:
    actor_id: str
    roles: frozenset[str]
    email: str


def _session_secret() -> str:
    secret = os.getenv("STUDIO_SESSION_SECRET", "").strip()
    if not secret:
        raise GoogleAuthError("STUDIO_SESSION_SECRET is required to issue or validate Studio sessions")
    return secret


def issue_session_token(account_id: str, email: str, global_role: str | None) -> str:
    """Sign a short-lived Studio session for an account.

    `global_role` is whatever persistence.py has on file right now; a
    pending account (no role yet) still gets a token, just one whose
    `roles` validates to an empty set, so require_global() denies it
    everywhere until an admin assigns a role.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "purpose": _SESSION_TOKEN_PURPOSE,
        "sub": account_id,
        "email": email,
        "role": global_role or "",
        "iat": now,
        "exp": now + timedelta(seconds=SESSION_TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, _session_secret(), algorithm="HS256")


def validate_session_token(token: str) -> SessionPrincipal:
    if not token or len(token) > 8 * 1024:
        raise GoogleAuthError("Session token is missing or exceeds the size limit")
    try:
        payload = jwt.decode(
            token,
            _session_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.InvalidTokenError as exc:
        raise GoogleAuthError("Session token validation failed") from exc
    if payload.get("purpose") != _SESSION_TOKEN_PURPOSE:
        raise GoogleAuthError("Token was not issued for a Studio session")
    actor_id = payload.get("sub")
    if not isinstance(actor_id, str) or not actor_id:
        raise GoogleAuthError("Session token has no stable subject")
    role = payload.get("role") or ""
    return SessionPrincipal(actor_id=actor_id, roles=frozenset({role}) if role else frozenset(), email=payload.get("email", ""))
