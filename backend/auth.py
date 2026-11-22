"""Microsoft Entra JWT validation boundary.

Cryptographic and issuer validation is separate from application authorization:
roles in a token never replace organization membership or assignment checks.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol
from urllib.request import Request, urlopen

import jwt


class TokenValidationError(ValueError):
    """Raised for any invalid or unsafe bearer token."""


@dataclass(frozen=True)
class EntraSettings:
    tenant_id: str
    audience: str
    issuer: str
    jwks_url: str
    web_client_id: str

    @classmethod
    def from_environment(cls) -> "EntraSettings":
        tenant_id = os.getenv("STUDIO_ENTRA_TENANT_ID", "").strip()
        audience = os.getenv("STUDIO_ENTRA_AUDIENCE", "").strip()
        web_client_id = os.getenv("STUDIO_ENTRA_WEB_CLIENT_ID", "").strip()
        if not tenant_id or not audience or not web_client_id:
            raise TokenValidationError("Studio tenant, audience and web client ID are required")
        issuer = os.getenv("STUDIO_ENTRA_ISSUER", f"https://login.microsoftonline.com/{tenant_id}/v2.0").strip()
        jwks_url = os.getenv("STUDIO_ENTRA_JWKS_URL", f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys").strip()
        return cls(tenant_id=tenant_id, audience=audience, issuer=issuer, jwks_url=jwks_url, web_client_id=web_client_id)


class SigningKeyProvider(Protocol):
    def key_for(self, key_id: str) -> Any:
        ...


class HttpJwksProvider:
    """Bounded JWKS client with an in-process cache."""

    def __init__(self, url: str, timeout_seconds: float = 3.0, cache_seconds: int = 300) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = cache_seconds
        self._expires_at = 0.0
        self._keys: dict[str, Any] = {}

    def key_for(self, key_id: str) -> Any:
        if monotonic() >= self._expires_at:
            self._refresh()
        key = self._keys.get(key_id)
        if key is None:
            raise TokenValidationError("The token signing key is not available")
        return key

    def _refresh(self) -> None:
        request = Request(self.url, headers={"Accept": "application/json"}, method="GET")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise TokenValidationError("The token signing-key endpoint returned an error")
                payload = json.loads(response.read(512 * 1024).decode("utf-8"))
        except TokenValidationError:
            raise
        except Exception as exc:
            raise TokenValidationError("The token signing-key endpoint could not be reached") from exc
        keys: dict[str, Any] = {}
        for item in payload.get("keys", []):
            key_id = item.get("kid")
            if key_id and item.get("kty") == "RSA":
                try:
                    keys[key_id] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(item))
                except Exception:
                    continue
        if not keys:
            raise TokenValidationError("The token signing-key response contained no usable RSA keys")
        self._keys = keys
        self._expires_at = monotonic() + self.cache_seconds


@dataclass(frozen=True)
class Principal:
    actor_id: str
    tenant_id: str
    roles: frozenset[str]
    claims: dict[str, Any]


class EntraTokenValidator:
    def __init__(self, settings: EntraSettings, key_provider: SigningKeyProvider) -> None:
        self.settings = settings
        self.key_provider = key_provider

    def validate(self, token: str) -> Principal:
        if not token or len(token) > 64 * 1024:
            raise TokenValidationError("Bearer token is missing or exceeds the size limit")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise TokenValidationError("Bearer token header is invalid") from exc
        if header.get("alg") not in {"RS256", "RS384", "RS512"} or not header.get("kid"):
            raise TokenValidationError("Bearer token algorithm or key identifier is not allowed")
        try:
            claims = jwt.decode(
                token,
                key=self.key_provider.key_for(header["kid"]),
                algorithms=[header["alg"]],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (jwt.InvalidTokenError, TokenValidationError) as exc:
            raise TokenValidationError("Bearer token validation failed") from exc
        token_tenant = claims.get("tid")
        if token_tenant != self.settings.tenant_id:
            raise TokenValidationError("Bearer token tenant does not match configuration")
        if claims.get("ver") != "2.0" or claims.get("azp") != self.settings.web_client_id:
            raise TokenValidationError("Studio requires a v2 access token issued to its web client")
        scopes = claims.get("scp")
        if not isinstance(scopes, str) or "Studio.Access" not in scopes.split() or claims.get("idtyp") == "app":
            raise TokenValidationError("A delegated Studio access token is required")
        actor_id = claims.get("oid")
        if not actor_id:
            raise TokenValidationError("Bearer token has no stable subject")
        raw_roles = claims.get("roles", [])
        roles = frozenset(role for role in raw_roles if isinstance(role, str)) if isinstance(raw_roles, list) else frozenset()
        if len(roles) != 1 or not roles.issubset({"admin", "reviewer", "professional", "client"}):
            raise TokenValidationError("Exactly one Studio workspace role is required")
        return Principal(actor_id=actor_id, tenant_id=token_tenant, roles=roles, claims=claims)
