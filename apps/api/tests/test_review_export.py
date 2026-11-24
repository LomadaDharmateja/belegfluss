"""Review (corrections), approval and accountant export (ADR-0017, ADR-0009)."""

import csv
import hashlib
import io
import uuid
import zipfile
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from belegfluss import export
from belegfluss.models import AuditEvent, Document, Invoice
from belegfluss.reading import Syntax, read_invoice
from belegfluss.worker import Worker
from tests.conftest import SignedInUser
from tests.pdfs import text_pdf
from tests.test_pipeline import CII, make_worker, upload


@pytest.fixture
def worker(client: TestClient, settings: object, validator_url: str) -> Worker:
    return make_worker(client, settings, validator_url)  # type: ignore[arg-type]


@pytest.fixture
def user(sign_in: Callable[[], SignedInUser]) -> SignedInUser:
    return sign_in()


def ai_document(
    client: TestClient, worker: Worker, user: SignedInUser, **model_changes: object
) -> uuid.UUID:
    """A plain PDF whose invoice was 'read by AI' (written directly, as the worker will do)."""
    unique = uuid.uuid4().hex[:8]
    pdf = text_pdf([f"Rechnung {unique}"])
    document_id = upload(client, user, f"scan-{unique}.pdf", pdf, "application/pdf")
    model = read_invoice(CII, Syntax.CII).model_copy(update=model_changes)
    with worker.services.session_factory.begin() as session:
        document = session.get_one(Document, document_id)
        session.add(
            Invoice(
                document_id=document_id,
                org_id=document.org_id,
                source="ai",
                number=model.number,
                issue_date=model.issue_date,
                seller_name=model.seller.name,
                seller_vat_id=model.seller.vat_id,
                currency=model.currency,
                net_total=model.totals.net,
                vat_total=model.totals.vat,
                gross_total=model.totals.gross,
                amount_due=model.totals.due,
                model=model.model_dump(mode="json"),
                pipeline_version="test",
                ai_model="fake",
            )
        )
        document.status = "needs_review"
    return document_id


def path(user: SignedInUser, document_id: uuid.UUID, action: str = "") -> str:
    return f"/orgs/{user.org_id}/documents/{document_id}{action}"


def audit_actions(worker: Worker, document_id: uuid.UUID) -> list[str]:
    with worker.services.session_factory() as session:
        return list(
            session.scalars(
                select(AuditEvent.action)
                .where(AuditEvent.target_id == document_id)
                .order_by(AuditEvent.at)
            )
        )


# --- corrections -----------------------------------------------------------------------------


def test_correcting_an_ai_invoice_records_before_and_after(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = ai_document(
        client, worker, user, number="RE-2O26-11O7"
    )  # letter O read instead of zero
    response = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"number": "RE-2026-1107"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["invoice"]["model"]["number"] == "RE-2026-1107"
    assert body["document"]["summary"]["number"] == "RE-2026-1107"
    assert [(r["field"], r["before"], r["after"]) for r in body["reviews"]] == [
        ("number", "RE-2O26-11O7", "RE-2026-1107")
    ]
    assert "invoice.corrected" in audit_actions(worker, document_id)


def test_a_correction_runs_the_checks_again(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = ai_document(client, worker, user)
    body = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"gross": "500.00"}
    ).json()
    assert "BF-TOTAL-GROSS" in {f["code"] for f in body["findings"]}
    body = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"gross": "447.40"}
    ).json()
    assert "BF-TOTAL-GROSS" not in {f["code"] for f in body["findings"]}


def test_xml_invoices_cannot_be_corrected(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")
    worker.run_once()
    response = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"number": "X"}
    )
    assert (response.status_code, response.json()["code"]) == (409, "invoice.not_editable")


def test_unknown_fields_are_rejected(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = ai_document(client, worker, user)
    response = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"status": "approved"}
    )
    assert response.status_code == 422


# --- approval --------------------------------------------------------------------------------


def test_approving_with_open_errors_needs_acknowledgement(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    broken = CII.replace(b"<ram:GrandTotalAmount>447.40<", b"<ram:GrandTotalAmount>500.00<")
    document_id = upload(client, user, "kaputt.xml", broken, "application/xml")
    worker.run_once()

    refused = client.post(path(user, document_id, "/approve"), headers=user.headers, json={})
    assert (refused.status_code, refused.json()["code"]) == (409, "document.has_errors")

    approved = client.post(
        path(user, document_id, "/approve"), headers=user.headers, json={"acknowledge_errors": True}
    )
    assert approved.status_code == 200
    assert approved.json()["document"]["status"] == "approved"
    assert approved.json()["document"]["approved_at"]
    assert "document.approved_with_errors" in audit_actions(worker, document_id)


def test_approve_is_idempotent_and_reopen_allows_corrections(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = ai_document(client, worker, user)
    for _ in range(2):
        assert (
            client.post(
                path(user, document_id, "/approve"), headers=user.headers, json={}
            ).status_code
            == 200
        )

    locked = client.patch(
        path(user, document_id, "/invoice"), headers=user.headers, json={"number": "X"}
    )
    assert (locked.status_code, locked.json()["code"]) == (409, "document.approved")

    reopened = client.post(path(user, document_id, "/reopen"), headers=user.headers)
    assert reopened.json()["document"]["status"] == "needs_review"
    assert (
        client.patch(
            path(user, document_id, "/invoice"), headers=user.headers, json={"number": "X"}
        ).status_code
        == 200
    )


def test_unprocessed_document_cannot_be_approved(client: TestClient, user: SignedInUser) -> None:
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")  # still "received"
    response = client.post(path(user, document_id, "/approve"), headers=user.headers, json={})
    assert (response.status_code, response.json()["code"]) == (409, "document.not_ready")


def test_other_organisations_get_404(
    client: TestClient, sign_in: Callable[[], SignedInUser], worker: Worker
) -> None:
    owner, stranger = sign_in(), sign_in()
    document_id = ai_document(client, worker, owner)
    for method, action, body in (
        ("patch", "/invoice", {"number": "X"}),
        ("post", "/approve", {}),
        ("post", "/reopen", None),
    ):
        response = client.request(
            method, path(owner, document_id, action), headers=stranger.headers, json=body
        )
        assert response.status_code == 404, (method, action)
    assert client.get(f"/orgs/{owner.org_id}/export", headers=stranger.headers).status_code == 404


# --- export ----------------------------------------------------------------------------------


def read_zip(response_content: bytes) -> tuple[zipfile.ZipFile, list[list[str]]]:
    archive = zipfile.ZipFile(io.BytesIO(response_content))
    rows = list(
        csv.reader(io.StringIO(archive.read("summary.csv").decode("utf-8-sig")), delimiter=";")
    )
    return archive, rows


def test_export_contains_only_approved_originals_unchanged_and_a_german_csv(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    xml_id = upload(client, user, "rechnung.xml", CII, "application/xml")
    worker.run_once()
    ai_id = ai_document(client, worker, user, number="RE-2026-2000")
    not_approved = ai_document(client, worker, user, number="RE-2026-3000")
    for document_id in (xml_id, ai_id):
        client.post(
            path(user, document_id, "/approve"),
            headers=user.headers,
            json={"acknowledge_errors": True},
        )

    response = client.get(f"/orgs/{user.org_id}/export", headers=user.headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    archive, rows = read_zip(response.content)

    with worker.services.session_factory() as session:
        hashes = {d.id: d.sha256 for d in session.scalars(select(Document))}
    originals = [name for name in archive.namelist() if name != "summary.csv"]
    assert len(originals) == 2
    assert sorted(hashlib.sha256(archive.read(n)).hexdigest() for n in originals) == sorted(
        [hashes[xml_id], hashes[ai_id]]
    )
    assert hashes[not_approved] not in {
        hashlib.sha256(archive.read(n)).hexdigest() for n in originals
    }

    header, *data = rows
    assert header[:4] == ["Datei", "Lieferant", "USt-IdNr. Lieferant", "Rechnungsnummer"]
    xml_row = next(r for r in data if r[3] == "RE-2026-1107")
    assert xml_row[1] == "Haustechnik Schäfer GmbH"
    assert xml_row[4] == "18.11.2026"
    assert (xml_row[7], xml_row[8], xml_row[9], xml_row[10]) == ("340,00", "64,60", "40,00", "2,80")
    assert xml_row[15] == "447,40"
    assert xml_row[0] in originals
    assert xml_row[0].startswith("2026-11-18_Haustechnik-Schäfer-GmbH_RE-2026-1107")


def test_export_filters_by_invoice_date(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = ai_document(client, worker, user)
    client.post(path(user, document_id, "/approve"), headers=user.headers, json={})
    inside = client.get(
        f"/orgs/{user.org_id}/export?from=2026-11-01&to=2026-11-30", headers=user.headers
    )
    outside = client.get(f"/orgs/{user.org_id}/export?from=2026-12-01", headers=user.headers)
    assert len(read_zip(inside.content)[1]) == 2  # header + one row
    assert len(read_zip(outside.content)[1]) == 1  # header only


def test_csv_cells_from_invoices_cannot_become_formulas(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    model = read_invoice(CII, Syntax.CII)
    seller = model.seller.model_copy(update={"name": '=HYPERLINK("http://evil.example","x")'})
    document_id = ai_document(client, worker, user, seller=seller)
    client.post(path(user, document_id, "/approve"), headers=user.headers, json={})
    _archive, rows = read_zip(
        client.get(f"/orgs/{user.org_id}/export", headers=user.headers).content
    )
    assert rows[1][1].startswith("'=")


def test_too_large_export_is_refused(
    client: TestClient, user: SignedInUser, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("belegfluss.routes.export.MAX_DOCUMENTS", 1)
    for _ in range(2):
        client.post(
            path(user, ai_document(client, worker, user), "/approve"), headers=user.headers, json={}
        )
    response = client.get(f"/orgs/{user.org_id}/export", headers=user.headers)
    assert (response.status_code, response.json()["code"]) == (413, "export.too_large")


def test_file_names_are_safe_and_unique() -> None:
    taken: set[str] = set()
    names = []
    for _ in range(2):
        invoice = Invoice(issue_date=None, seller_name="../../etc/passwd", number="A/B C")
        document = Document(media_type="application/pdf", id=uuid.uuid4(), blob_name="x")
        names.append(export.file_name(export.ExportItem(document, invoice), taken))
    assert names == ["etc-passwd_A-B-C.pdf", "etc-passwd_A-B-C-2.pdf"]
