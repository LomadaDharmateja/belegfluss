"""Access-token validation for Entra External ID (ADR-0003).

The API is the security boundary: every protected route depends on `current_principal`, which
validates signature, issuer, audience, expiry and scope. There is no switch to skip validation.
Tests inject a different key source (a local key pair) instead of the tenant's JWKS endpoint.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Protocol

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from belegfluss.errors import AppError

ALGORITHMS = ["RS256"]


@dataclass(frozen=True)
class Principal:
    """The signed-in person as identified by the token. `oid` is the stable user ID."""

    tenant_id: str
    object_id: str


class KeySource(Protocol):
    def signing_key_for(self, token: str) -> Any: ...


class JwksKeySource:
    """Fetches (and caches) the tenant's public signing keys on first use."""

    def __init__(self, jwks_url: str) -> None:
        self._jwks_url = jwks_url
        self._client: jwt.PyJWKClient | None = None

    def signing_key_for(self, token: str) -> Any:
        if self._client is None:
            self._client = jwt.PyJWKClient(self._jwks_url, cache_keys=True, lifespan=3600)
        return self._client.get_signing_key_from_jwt(token).key


class TokenVerifier:
    def __init__(self, keys: KeySource, *, issuer: str, audience: str, required_scope: str) -> None:
        self._keys = keys
        self._issuer = issuer
        self._audience = audience
        self._required_scope = required_scope

    def verify(self, token: str) -> Principal:
        if not (self._issuer and self._audience):
            raise AppError(503, "auth.not_configured", "Sign-in is not configured on the server.")
        try:
            key = self._keys.signing_key_for(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "tid", "oid"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AppError(401, "auth.token_expired", "The access token has expired.") from exc
        except jwt.PyJWTError as exc:
            raise AppError(401, "auth.invalid_token", "The access token is not valid.") from exc

        scopes = str(claims.get("scp", "")).split()
        if self._required_scope not in scopes:
            raise AppError(403, "auth.insufficient_scope", "The access token lacks the API scope.")
        return Principal(tenant_id=str(claims["tid"]), object_id=str(claims["oid"]))


_bearer = HTTPBearer(auto_error=False)


def current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None:
        raise AppError(401, "auth.missing_token", "Sign-in required.")
    verifier: TokenVerifier = request.app.state.verifier
    return verifier.verify(credentials.credentials)
