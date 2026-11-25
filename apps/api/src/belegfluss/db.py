"""Database engine and per-request sessions (sync SQLAlchemy, see ADR-0012)."""

from collections.abc import Callable, Iterator
from typing import Any

from azure.core.credentials import TokenCredential
from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from belegfluss.identity import azure_credential

# Azure Database for PostgreSQL accepts Microsoft Entra access tokens for this resource as password.
POSTGRES_TOKEN_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"  # noqa: S105
# Tokens are checked when a connection opens; renewing pooled connections well within a token's
# lifetime (about an hour) keeps that true for long-running processes as well.
ENTRA_POOL_RECYCLE_SECONDS = 30 * 60


def make_engine(
    database_url: str, entra_auth: bool = False, credential: TokenCredential | None = None
) -> Engine:
    """Locally the URL holds the password. With `entra_auth` (Azure, ADR-0021) it holds none, and
    every new connection gets a fresh token from the Managed Identity instead."""
    if not entra_auth:
        return create_engine(database_url, pool_pre_ping=True)
    engine = create_engine(
        database_url, pool_pre_ping=True, pool_recycle=ENTRA_POOL_RECYCLE_SECONDS
    )
    event.listen(engine, "do_connect", _token_as_password(credential or azure_credential()))
    return engine


def _token_as_password(credential: TokenCredential) -> Callable[..., None]:
    def set_password(_dialect: Any, _record: Any, _args: Any, params: dict[str, Any]) -> None:
        params["password"] = credential.get_token(POSTGRES_TOKEN_SCOPE).token

    return set_password


def make_session_factory(
    database_url: str, entra_auth: bool = False
) -> tuple[Engine, sessionmaker[Session]]:
    engine = make_engine(database_url, entra_auth)
    return engine, sessionmaker(engine, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    """One session per request. Routes commit explicitly; anything uncommitted is rolled back."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
