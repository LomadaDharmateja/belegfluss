"""Upload: accepted types, limits, duplicates, unchanged originals, audit."""

import hashlib
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from belegfluss.models import AuditEvent
from belegfluss.storage import BlobStore
from tests.conftest import MAX_UPLOAD_BYTES, SignedInUser

XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<ubl:Invoice xmlns:ubl="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
    b"<cbc:Note>Gr\xc3\xbc\xc3\x9fe aus K\xc3\xb6ln</cbc:Note></ubl:Invoice>\n"
)
PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


@pytest.mark.parametrize(
    ("content", "filename", "media_type"),
    [
        (XML, "rechnung.xml", "application/xml"),
        (PDF, "rechnung.pdf", "application/pdf"),
        (PNG, "beleg.png", "image/png"),
        (JPEG, "beleg.jpg", "image/jpeg"),
        (b"\xef\xbb\xbf \n" + XML, "bom.xml", "application/xml"),
    ],
)
def test_supported_files_are_stored_unchanged(
    client: TestClient,
    sign_in: Callable[[], SignedInUser],
    content: bytes,
    filename: str,
    media_type: str,
) -> None:
    user = sign_in()
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": (filename, content, "application/octet-stream")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["duplicate"] is False
    doc = body["document"]
    sha256 = hashlib.sha256(content).hexdigest()
    assert doc["media_type"] == media_type  # detected from content, not from the name
    assert doc["sha256"] == sha256
    assert doc["size_bytes"] == len(content)
    assert doc["status"] == "received"
    assert doc["original_filename"] == filename

    store: BlobStore = client.app.state.blob_store  # type: ignore[attr-defined]
    stored = store.read(BlobStore.original_name(uuid.UUID(user.org_id), sha256))
    assert stored == content  # byte-identical original


@pytest.mark.parametrize(
    "content",
    [
        b"MZ\x90\x00\x03\x00\x00\x00",  # Windows executable
        b"<!DOCTYPE html><html><body>hi</body></html>",
        b"<html><body>hi</body></html>",
        b"Hallo, das ist nur Text.",
        b"PK\x03\x04zip",
    ],
)
def test_unsupported_content_is_415(
    client: TestClient, sign_in: Callable[[], SignedInUser], content: bytes
) -> None:
    user = sign_in()
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("looks-like.pdf", content, "application/pdf")},
    )
    assert response.status_code == 415
    assert response.json()["code"] == "upload.unsupported_type"


def test_empty_file_is_400(client: TestClient, sign_in: Callable[[], SignedInUser]) -> None:
    user = sign_in()
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "upload.empty"


def test_too_large_file_is_413(client: TestClient, sign_in: Callable[[], SignedInUser]) -> None:
    user = sign_in()
    too_big = b"%PDF-1.7\n" + b"0" * MAX_UPLOAD_BYTES
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("big.pdf", too_big, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "upload.too_large"
    listed = client.get(f"/orgs/{user.org_id}/documents", headers=user.headers).json()
    assert listed == []


def test_same_bytes_twice_returns_existing_document(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    user = sign_in()
    first = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("a.xml", XML, "application/xml")},
    )
    second = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("copy-of-a.xml", XML, "application/xml")},
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["document"]["id"] == first.json()["document"]["id"]
    listed = client.get(f"/orgs/{user.org_id}/documents", headers=user.headers).json()
    assert len(listed) == 1


def test_file_names_are_sanitised(client: TestClient, sign_in: Callable[[], SignedInUser]) -> None:
    user = sign_in()
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("..\\..\\windows\\Rechnung März.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["document"]["original_filename"] == "Rechnung März.pdf"


def test_list_is_newest_first_and_get_by_id_works(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    user = sign_in()
    ids = []
    for content in (XML, PDF, PNG):
        response = client.post(
            f"/orgs/{user.org_id}/documents",
            headers=user.headers,
            files={"file": ("f", content, "application/octet-stream")},
        )
        ids.append(response.json()["document"]["id"])
    listed = client.get(f"/orgs/{user.org_id}/documents", headers=user.headers).json()
    assert [d["id"] for d in listed] == list(reversed(ids))
    single = client.get(f"/orgs/{user.org_id}/documents/{ids[0]}", headers=user.headers)
    assert single.status_code == 200
    body = single.json()
    assert body["document"]["id"] == ids[0]
    assert (body["invoice"], body["findings"]) == (None, [])  # not processed yet


def test_upload_is_audited_without_file_name(
    client: TestClient, sign_in: Callable[[], SignedInUser]
) -> None:
    user = sign_in()
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": ("secret-client-name.pdf", PDF, "application/pdf")},
    )
    doc_id = uuid.UUID(response.json()["document"]["id"])
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        event = session.scalars(
            select(AuditEvent).where(AuditEvent.action == "document.uploaded")
        ).one()
    assert event.target_id == doc_id
    assert str(event.org_id) == user.org_id
    assert str(event.actor_user_id) == user.user_id
    # The audit table has no free-text column at all, so a file name can't end up there.
    assert set(AuditEvent.__table__.columns.keys()) == {
        "id",
        "org_id",
        "actor_user_id",
        "action",
        "target_id",
        "at",
    }
