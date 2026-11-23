"""Access-token validation: every way a token can be wrong must be rejected."""

import uuid
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from belegfluss.main import create_app
from belegfluss.settings import Settings
from tests.conftest import bearer, make_token


def _error_code(response: Any) -> str:
    return str(response.json()["code"])


def test_missing_token_is_401(client: TestClient) -> None:
    response = client.get("/me")
    assert response.status_code == 401
    assert _error_code(response) == "auth.missing_token"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_garbage_token_is_401(client: TestClient) -> None:
    response = client.get("/me", headers=bearer("not-a-jwt"))
    assert response.status_code == 401
    assert _error_code(response) == "auth.invalid_token"


def test_valid_token_is_accepted(client: TestClient, signing_key: Any) -> None:
    response = client.get("/me", headers=bearer(make_token(signing_key, oid=str(uuid.uuid4()))))
    assert response.status_code == 200


def test_expired_token_is_401(client: TestClient, signing_key: Any) -> None:
    token = make_token(signing_key, oid=str(uuid.uuid4()), expires_in=-60)
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 401
    assert _error_code(response) == "auth.token_expired"


def test_wrong_audience_is_401(client: TestClient, signing_key: Any) -> None:
    token = make_token(signing_key, oid=str(uuid.uuid4()), aud="some-other-api")
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 401
    assert _error_code(response) == "auth.invalid_token"


def test_wrong_issuer_is_401(client: TestClient, signing_key: Any) -> None:
    token = make_token(signing_key, oid=str(uuid.uuid4()), iss="https://evil.example/v2.0")
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 401
    assert _error_code(response) == "auth.invalid_token"


def test_token_signed_by_unknown_key_is_401(client: TestClient) -> None:
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(attacker_key, oid=str(uuid.uuid4()))
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 401
    assert _error_code(response) == "auth.invalid_token"


def test_unsigned_token_is_401(client: TestClient) -> None:
    claims = jwt.decode(
        make_token(rsa.generate_private_key(public_exponent=65537, key_size=2048), oid="x"),
        options={"verify_signature": False},
    )
    unsigned = jwt.encode(claims, key=None, algorithm="none")
    response = client.get("/me", headers=bearer(unsigned))
    assert response.status_code == 401


def test_token_without_oid_is_401(client: TestClient, signing_key: Any) -> None:
    token = make_token(signing_key, oid=str(uuid.uuid4()), omit=("oid",))
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 401


def test_token_without_api_scope_is_403(client: TestClient, signing_key: Any) -> None:
    token = make_token(signing_key, oid=str(uuid.uuid4()), scp="User.Read")
    response = client.get("/me", headers=bearer(token))
    assert response.status_code == 403
    assert _error_code(response) == "auth.insufficient_scope"


def test_unconfigured_server_refuses_with_503(settings: Settings, signing_key: Any) -> None:
    unconfigured = settings.model_copy(update={"auth_issuer": "", "auth_audience": ""})
    app = create_app(unconfigured)  # default verifier, as in production
    with TestClient(app) as client:
        token = make_token(signing_key, oid=str(uuid.uuid4()))
        response = client.get("/me", headers=bearer(token))
    app.state.engine.dispose()
    assert response.status_code == 503
    assert _error_code(response) == "auth.not_configured"


def test_health_needs_no_token(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
