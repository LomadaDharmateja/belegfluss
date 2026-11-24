"""Upload -> queue -> worker -> invoice + findings, with real PostgreSQL, Azurite and the validator.

Includes the fault cases from ADR-0004: failed enqueue (sweeper), repeated failure (poison),
re-processing.
"""

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from azure.core.exceptions import ServiceRequestError
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from belegfluss.models import Document, Finding, Invoice
from belegfluss.pipeline import Services, process_document
from belegfluss.queue import DocumentQueue
from belegfluss.settings import Settings
from belegfluss.validation import ValidatorClient
from belegfluss.worker import Worker
from tests.conftest import SignedInUser
from tests.pdfs import text_pdf, zugferd_pdf

FIXTURES = Path(__file__).parent / "fixtures"
CII = (FIXTURES / "invoice_cii.xml").read_bytes()


def make_worker(client: TestClient, settings: Settings, validator_url: str) -> Worker:
    state = client.app.state  # type: ignore[attr-defined]
    services = Services(
        session_factory=state.session_factory,
        blob_store=state.blob_store,
        validator=ValidatorClient(validator_url, timeout_seconds=10),
        validator_config=settings.validator_config,
        max_pdf_pages=settings.max_pdf_pages,
    )
    queue = DocumentQueue(settings.storage_connection_string, settings.queue_name)
    queue.ensure_exists()
    return Worker(services, queue, visibility_timeout=1)


@pytest.fixture
def worker(client: TestClient, settings: Settings, validator_url: str) -> Worker:
    return make_worker(client, settings, validator_url)


@pytest.fixture
def user(sign_in: Callable[[], SignedInUser]) -> SignedInUser:
    return sign_in()


def upload(
    client: TestClient, user: SignedInUser, name: str, data: bytes, media_type: str
) -> uuid.UUID:
    response = client.post(
        f"/orgs/{user.org_id}/documents",
        headers=user.headers,
        files={"file": (name, data, media_type)},
    )
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["document"]["id"])


def state_of(
    worker: Worker, document_id: uuid.UUID
) -> tuple[Document, Invoice | None, list[Finding]]:
    with worker.services.session_factory() as session:
        document = session.get_one(Document, document_id)
        invoice = session.scalars(
            select(Invoice).where(Invoice.document_id == document_id)
        ).one_or_none()
        findings = list(session.scalars(select(Finding).where(Finding.document_id == document_id)))
        return document, invoice, findings


def codes(findings: list[Finding]) -> set[str]:
    return {f.code for f in findings}


def test_xml_invoice_is_read_validated_and_ready(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")
    assert worker.run_once() == 1

    document, invoice, findings = state_of(worker, document_id)
    assert document.status == "ready"
    assert invoice is not None
    assert (invoice.source, invoice.syntax, invoice.number) == ("xml", "cii", "RE-2026-1107")
    assert str(invoice.gross_total) == "447.40"
    assert invoice.validation_outcome == "accepted"
    assert invoice.validator_engine == "KoSIT Validator 1.6.3"
    assert invoice.validator_config == "xrechnung-3.0.2-2026-08-31"
    assert invoice.model["seller"]["name"] == "Haustechnik Schäfer GmbH"
    assert not [f for f in findings if f.severity == "error"]


def test_wrong_total_needs_review_with_the_official_rule(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    broken = CII.replace(b"<ram:GrandTotalAmount>447.40<", b"<ram:GrandTotalAmount>500.00<")
    document_id = upload(client, user, "kaputt.xml", broken, "application/xml")
    worker.run_once()

    document, invoice, findings = state_of(worker, document_id)
    assert document.status == "needs_review"
    assert invoice is not None and invoice.validation_outcome == "rejected"
    br_co_15 = next(f for f in findings if f.code == "BR-CO-15")
    assert (br_co_15.origin, br_co_15.severity) == ("kosit", "error")
    assert "BT-112" in br_co_15.business_terms
    assert br_co_15.message


def test_unsafe_xml_needs_review_without_reaching_the_validator(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    unsafe = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "a">]><x>&a;</x>'
    document_id = upload(client, user, "unsafe.xml", unsafe, "application/xml")
    worker.run_once()

    document, invoice, findings = state_of(worker, document_id)
    assert (document.status, invoice) == ("needs_review", None)
    assert codes(findings) == {"BF-XML-DOCTYPE"}


def test_plain_pdf_waits_for_ai_reading(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = upload(client, user, "scan.pdf", text_pdf(["Rechnung 4711"]), "application/pdf")
    worker.run_once()

    document, invoice, findings = state_of(worker, document_id)
    assert (document.status, invoice) == ("needs_review", None)
    assert codes(findings) == {"BF-UNSTRUCTURED"}


def test_zugferd_pdf_is_compared_with_its_xml(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    pdf = zugferd_pdf(CII, ["Rechnung RE-2026-9999", "Gesamtbetrag 447,40 EUR"])
    document_id = upload(client, user, "zugferd.pdf", pdf, "application/pdf")
    worker.run_once()

    document, invoice, findings = state_of(worker, document_id)
    assert invoice is not None and invoice.source == "zugferd"
    assert "BF-PDF-XML-MISMATCH-NUMBER" in codes(findings)
    assert "BF-PDF-XML-MISMATCH-TOTAL" not in codes(findings)
    assert document.status == "ready"  # a warning: the XML is leading, the user should check


def test_zugferd_minimum_is_not_an_e_invoice(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    minimum = CII.replace(
        b"<ram:ID>urn:cen.eu:en16931:2017</ram:ID>", b"<ram:ID>urn:factur-x.eu:1p0:minimum</ram:ID>"
    )
    pdf = zugferd_pdf(minimum, ["Rechnung RE-2026-1107", "Summe 447,40 EUR"], level="minimum")
    document_id = upload(client, user, "minimum.pdf", pdf, "application/pdf")
    worker.run_once()

    _document, _invoice, findings = state_of(worker, document_id)
    assert "BF-NOT-AN-E-INVOICE" in codes(findings)


def test_same_invoice_in_other_bytes_is_a_semantic_duplicate(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    first = upload(client, user, "a.xml", CII, "application/xml")
    worker.run_once()
    second = upload(
        client,
        user,
        "b.xml",
        CII.replace(b"</rsm:CrossIndustryInvoice>", b"\n</rsm:CrossIndustryInvoice>"),
        "application/xml",
    )
    worker.run_once()

    _document, _invoice, findings = state_of(worker, second)
    duplicate = next(f for f in findings if f.code == "BF-DUPLICATE")
    assert duplicate.params == {"document_id": str(first)}


def test_reprocessing_replaces_results(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")
    worker.run_once()
    _document, _invoice, before = state_of(worker, document_id)

    with worker.services.session_factory.begin() as session:
        session.execute(
            update(Document).where(Document.id == document_id).values(status="received")
        )
    assert process_document(document_id, worker.services) is True

    with worker.services.session_factory() as session:
        invoices = session.scalar(select(func.count()).where(Invoice.document_id == document_id))
        findings = session.scalar(select(func.count()).where(Finding.document_id == document_id))
    assert (invoices, findings) == (1, len(before))


def test_done_document_is_not_processed_again(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")
    worker.run_once()
    assert process_document(document_id, worker.services) is False


def test_sweeper_picks_up_a_document_whose_enqueue_failed(
    client: TestClient, user: SignedInUser, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_send(_document_id: uuid.UUID) -> None:
        raise ServiceRequestError("queue down")

    monkeypatch.setattr(client.app.state.queue, "send", broken_send)  # type: ignore[attr-defined]
    document_id = upload(
        client, user, "rechnung.xml", CII, "application/xml"
    )  # upload still succeeds
    assert worker.run_once() == 0

    with worker.services.session_factory.begin() as session:
        session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status_changed_at=datetime.now(UTC) - timedelta(minutes=3))
        )
    assert worker.sweep(datetime.now(UTC)) == 1
    assert worker.run_once() == 1
    assert state_of(worker, document_id)[0].status == "ready"


def test_document_that_keeps_failing_ends_failed_and_in_the_poison_queue(
    client: TestClient, user: SignedInUser, settings: Settings
) -> None:
    worker = make_worker(client, settings, "http://127.0.0.1:9")  # validator unreachable
    document_id = upload(client, user, "rechnung.xml", CII, "application/xml")

    for _ in range(worker.max_deliveries + 1):
        assert worker.run_once() == 1
        time.sleep(1.2)  # minimum visibility timeout is 1 s

    document, _invoice, _findings = state_of(worker, document_id)
    assert (document.status, document.failure_reason) == ("failed", "processing.gave_up")
    assert worker.run_once() == 0
    assert worker.queue.peek_poison() == [f'{{"document_id": "{document_id}"}}']


def test_list_and_detail_show_what_was_read(
    client: TestClient, user: SignedInUser, worker: Worker
) -> None:
    broken = CII.replace(b"<ram:GrandTotalAmount>447.40<", b"<ram:GrandTotalAmount>500.00<")
    document_id = upload(client, user, "kaputt.xml", broken, "application/xml")
    worker.run_once()

    listed = client.get(f"/orgs/{user.org_id}/documents", headers=user.headers).json()
    assert listed[0]["status"] == "needs_review"
    assert listed[0]["summary"] == {
        "number": "RE-2026-1107",
        "issue_date": "2026-11-18",
        "seller_name": "Haustechnik Schäfer GmbH",
        "currency": "EUR",
        "gross_total": "500.00",
    }
    assert listed[0]["finding_counts"]["error"] >= 1

    detail = client.get(f"/orgs/{user.org_id}/documents/{document_id}", headers=user.headers).json()
    assert detail["invoice"]["validation_outcome"] == "rejected"
    assert detail["invoice"]["model"]["lines"][1]["name"] == "Fachbuch „Wärmepumpen“"
    assert detail["findings"][0]["severity"] == "error"  # errors first
    assert any(
        f["code"] == "BR-CO-15" and "BT-112" in f["business_terms"] for f in detail["findings"]
    )


def test_detail_of_another_organisation_is_404(
    client: TestClient, sign_in: Callable[[], SignedInUser], worker: Worker
) -> None:
    owner, stranger = sign_in(), sign_in()
    document_id = upload(client, owner, "rechnung.xml", CII, "application/xml")
    worker.run_once()
    response = client.get(f"/orgs/{owner.org_id}/documents/{document_id}", headers=stranger.headers)
    assert response.status_code == 404
