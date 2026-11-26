"""Database sign-in with a Microsoft Entra token instead of a stored password (ADR-0021).

The real PostgreSQL container stands in for Azure: the fake credential returns the container's
password as the "token", so the test proves that every new connection asks the credential for its
password, with the PostgreSQL scope, and that the URL needs no password at all.
"""

from typing import Any

import pytest
from azure.core.credentials import AccessToken
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError

from belegfluss.db import POSTGRES_TOKEN_SCOPE, make_engine


def _without_password(url: URL) -> str:
    # URL.set(password=None) would keep the password (None means "unchanged" there).
    bare = URL.create(url.drivername, url.username, None, url.host, url.port, url.database)
    assert bare.password is None
    return bare.render_as_string(hide_password=False)


class FakeCredential:
    def __init__(self, token: str) -> None:
        self.token = token
        self.scopes: list[str] = []

    def get_token(self, *scopes: str, **_kwargs: Any) -> AccessToken:
        self.scopes.extend(scopes)
        return AccessToken(self.token, 0)


def test_with_entra_auth_each_new_connection_uses_a_fresh_token_as_password(
    postgres_url: str,
) -> None:
    url = make_url(postgres_url)
    credential = FakeCredential(token=str(url.password))
    without_password = _without_password(url)

    engine = make_engine(without_password, entra_auth=True, credential=credential)
    with engine.connect() as connection:
        assert connection.scalar(text("select 1")) == 1
    engine.dispose()
    with engine.connect() as connection:  # a new connection after dispose: a new token
        assert connection.scalar(text("select 1")) == 1
    engine.dispose()

    assert credential.scopes == [POSTGRES_TOKEN_SCOPE, POSTGRES_TOKEN_SCOPE]


def test_without_entra_auth_no_token_is_used(postgres_url: str) -> None:
    url = make_url(postgres_url)
    without_password = _without_password(url)
    credential = FakeCredential(token=str(url.password))

    engine = make_engine(without_password, entra_auth=False, credential=credential)
    with pytest.raises(OperationalError), engine.connect():
        pass
    engine.dispose()
    assert credential.scopes == []
