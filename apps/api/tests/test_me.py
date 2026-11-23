"""First sign-in creates a user and a personal organisation; later sign-ins reuse them."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from belegfluss.models import AuditEvent
from tests.conftest import bearer, make_token


def test_first_sign_in_creates_user_and_personal_org(client: TestClient, signing_key: Any) -> None:
    response = client.get("/me", headers=bearer(make_token(signing_key, oid=str(uuid.uuid4()))))
    assert response.status_code == 200
    body = response.json()
    assert len(body["organizations"]) == 1
    assert body["organizations"][0]["role"] == "owner"
    assert body["organizations"][0]["name"] == "My business"


def test_second_sign_in_reuses_user_and_org(client: TestClient, signing_key: Any) -> None:
    oid = str(uuid.uuid4())
    first = client.get("/me", headers=bearer(make_token(signing_key, oid=oid))).json()
    second = client.get("/me", headers=bearer(make_token(signing_key, oid=oid))).json()
    assert first == second


def test_different_users_get_different_orgs(client: TestClient, signing_key: Any) -> None:
    a = client.get("/me", headers=bearer(make_token(signing_key, oid=str(uuid.uuid4())))).json()
    b = client.get("/me", headers=bearer(make_token(signing_key, oid=str(uuid.uuid4())))).json()
    assert a["user_id"] != b["user_id"]
    assert a["organizations"][0]["id"] != b["organizations"][0]["id"]


def test_first_sign_in_is_audited(client: TestClient, signing_key: Any) -> None:
    body = client.get("/me", headers=bearer(make_token(signing_key, oid=str(uuid.uuid4())))).json()
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        actions = set(
            session.scalars(
                select(AuditEvent.action).where(
                    AuditEvent.actor_user_id == uuid.UUID(body["user_id"])
                )
            )
        )
    assert actions == {"user.created", "org.created"}
