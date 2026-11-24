"""Test fixtures: PostgreSQL 18, Azurite and the KoSIT validator in containers; test tokens."""

import subprocess
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import text
from testcontainers.community.azurite import AzuriteContainer
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from belegfluss.auth import TokenVerifier
from belegfluss.main import create_app
from belegfluss.settings import Settings

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]

ISSUER = "https://test-tenant.ciamlogin.com/00000000-0000-0000-0000-000000000001/v2.0"
AUDIENCE = "00000000-0000-0000-0000-0000000000a1"
SCOPE = "access_as_user"
TENANT_ID = "00000000-0000-0000-0000-000000000001"
MAX_UPLOAD_BYTES = 1024 * 1024


class StaticKeySource:
    """Test replacement for the tenant's JWKS endpoint: one known public key."""

    def __init__(self, public_key: Any) -> None:
        self._key = public_key

    def signing_key_for(self, token: str) -> Any:
        return self._key


def make_token(
    private_key: Any,
    *,
    oid: str,
    tid: str = TENANT_ID,
    aud: str = AUDIENCE,
    iss: str = ISSUER,
    scp: str = SCOPE,
    expires_in: int = 300,
    omit: tuple[str, ...] = (),
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "tid": tid,
        "oid": oid,
        "scp": scp,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    for name in omit:
        claims.pop(name)
    return jwt.encode(claims, private_key, algorithm="RS256")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def run_migrations(database_url: str, revision: str = "head") -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, revision)


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:18-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_db(postgres_url: str) -> str:
    run_migrations(postgres_url)
    return postgres_url


@pytest.fixture(scope="session")
def azurite_connection_string() -> Iterator[str]:
    # Same image and flag as compose.yaml: the newest Azure SDKs send API versions that Azurite
    # doesn't list yet.
    azurite = AzuriteContainer(
        "mcr.microsoft.com/azure-storage/azurite:3.38.0",
        command="azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0"
        " --skipApiVersionCheck",
    )
    with azurite:
        yield azurite.get_connection_string()


VALIDATOR_IMAGE = "belegfluss-validator:test"


@pytest.fixture(scope="session")
def validator_url() -> Iterator[str]:
    """The real validator image from services/validator. Built with the docker CLI, because the
    Dockerfile uses BuildKit features (ADD --checksum) that the Docker SDK can't build."""
    command = ["docker", "build", "--quiet", "--tag", VALIDATOR_IMAGE, "services/validator"]
    subprocess.run(  # noqa: S603
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    container = (
        DockerContainer(VALIDATOR_IMAGE)
        .with_exposed_ports(8080)
        .waiting_for(LogMessageWaitStrategy("Daemon started").with_startup_timeout(120))
    )
    with container:
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"


@pytest.fixture(scope="session")
def signing_key() -> Any:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(migrated_db: str, azurite_connection_string: str) -> Settings:
    return Settings(
        database_url=migrated_db,
        storage_connection_string=azurite_connection_string,
        blob_container=f"test-{uuid.uuid4().hex[:12]}",
        queue_name=f"test-{uuid.uuid4().hex[:12]}",
        auth_issuer=ISSUER,
        auth_audience=AUDIENCE,
        auth_required_scope=SCOPE,
        max_upload_bytes=MAX_UPLOAD_BYTES,
    )


@pytest.fixture
def client(settings: Settings, signing_key: Any) -> Iterator[TestClient]:
    verifier = TokenVerifier(
        StaticKeySource(signing_key.public_key()),
        issuer=ISSUER,
        audience=AUDIENCE,
        required_scope=SCOPE,
    )
    app = create_app(settings, verifier=verifier)
    with TestClient(app) as test_client:
        yield test_client
    with app.state.engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE findings, invoices, audit_events, documents, memberships, users,"
                " organizations"
            )
        )
    app.state.engine.dispose()


@dataclass(frozen=True)
class SignedInUser:
    headers: dict[str, str]
    user_id: str
    org_id: str


@pytest.fixture
def sign_in(client: TestClient, signing_key: Any) -> Callable[[], SignedInUser]:
    """Create a new user (new `oid`) by calling /me once, like the web app does after sign-in."""

    def _sign_in() -> SignedInUser:
        headers = bearer(make_token(signing_key, oid=str(uuid.uuid4())))
        me = client.get("/me", headers=headers)
        assert me.status_code == 200, me.text
        body = me.json()
        return SignedInUser(headers, body["user_id"], body["organizations"][0]["id"])

    return _sign_in
