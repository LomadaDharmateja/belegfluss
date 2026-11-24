"""One organisation must never see or change another organisation's documents (ADR-0013)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import SignedInUser

PDF = b"%PDF-1.7\n%%EOF\n"


def _upload(client: TestClient, user: SignedInUser) -> str:
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("a.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 201
    return str(response.json()["document"]["id"])


def test_other_user_cannot_list_documents(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    alice, bob = sign_in(), sign_in()
    _upload(client, alice)
    response = client.get(f"/orgs/{alice.org_id}/documents", headers=bob.headers)
    assert response.status_code == 404
    assert response.json()["code"] == "org.not_found"


def test_other_user_cannot_read_a_document(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    alice, bob = sign_in(), sign_in()
    doc_id = _upload(client, alice)
    via_alices_org = client.get(f"/orgs/{alice.org_id}/documents/{doc_id}", headers=bob.headers)
    via_bobs_org = client.get(f"/orgs/{bob.org_id}/documents/{doc_id}", headers=bob.headers)
    assert via_alices_org.status_code == 404
    assert via_bobs_org.status_code == 404
    assert via_bobs_org.json()["code"] == "document.not_found"


def test_other_user_cannot_upload_into_an_org(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    alice, bob = sign_in(), sign_in()
    response = client.post(
        f"/orgs/{alice.org_id}/documents",
        headers=bob.headers,
        files={"file": ("x.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 404
    assert client.get(f"/orgs/{alice.org_id}/documents", headers=alice.headers).json() == []


def test_same_file_in_two_orgs_is_two_documents(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    alice, bob = sign_in(), sign_in()
    assert _upload(client, alice) != _upload(client, bob)


def test_unknown_org_is_404(client: TestClient, sign_in: Callable[[], SignedInUser]) -> None:
    alice = sign_in()
    response = client.get(f"/orgs/{uuid.uuid4()}/documents", headers=alice.headers)
    assert response.status_code == 404


def test_owner_still_sees_own_document(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    alice, _bob = sign_in(), sign_in()
    doc_id = _upload(client, alice)
    response = client.get(f"/orgs/{alice.org_id}/documents/{doc_id}", headers=alice.headers)
    assert response.status_code == 200
