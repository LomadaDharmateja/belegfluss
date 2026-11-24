"""Process one document: classify -> read -> validate -> check -> save (ARCHITECTURE §4).

Steps that take time (reading, the validator) run without an open transaction. Saving replaces
earlier results for the document, so processing it twice gives the same rows (ADR-0004).
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, sessionmaker

from belegfluss import audit
from belegfluss.checks import Context, check_invoice
from belegfluss.models import Document, DocumentStatus, Finding, Invoice
from belegfluss.reading import InvoiceModel, ReadingError, Source, Syntax, classify, read_invoice
from belegfluss.storage import BlobStore
from belegfluss.validation import Outcome, ValidationResult

PIPELINE_VERSION = "m2a.1"
DONE = {DocumentStatus.READY, DocumentStatus.NEEDS_REVIEW, DocumentStatus.FAILED}
_TERM = re.compile(r"\b(B[TG]-\d+)\b")


class Validator(Protocol):
    def validate(self, xml: bytes) -> ValidationResult: ...


@dataclass(frozen=True)
class NewFinding:
    origin: str  # kosit | belegfluss
    code: str
    severity: str
    message: str | None = None
    location: str | None = None
    business_terms: tuple[str, ...] = ()
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class Analysis:
    findings: list[NewFinding] = field(default_factory=list)
    invoice: InvoiceModel | None = None
    source: Source | None = None
    syntax: Syntax | None = None
    pdf_text: str | None = None
    validation: ValidationResult | None = None


@dataclass(frozen=True)
class Services:
    session_factory: sessionmaker[Session]
    blob_store: BlobStore
    validator: Validator
    validator_config: str
    max_pdf_pages: int


def _now() -> datetime:
    return datetime.now(UTC)


def _kosit_findings(result: ValidationResult) -> list[NewFinding]:
    findings = [
        NewFinding(
            origin="kosit",
            code=m.code,
            severity=m.severity,
            message=m.text,
            location=m.location,
            business_terms=tuple(dict.fromkeys(_TERM.findall(m.text))),
        )
        for m in result.messages
    ]
    if result.outcome is Outcome.NOT_PROCESSABLE:
        findings.append(NewFinding("belegfluss", "BF-VALIDATOR-NOT-PROCESSABLE", "warning"))
    return findings


def analyse(data: bytes, media_type: str, services: Services) -> Analysis:
    """Everything that needs no database: read the document and run the official validator."""
    analysis = Analysis()
    try:
        classified = classify(data, media_type, max_pdf_pages=services.max_pdf_pages)
        analysis.source, analysis.syntax = classified.source, classified.syntax
        analysis.pdf_text = classified.pdf_text
        if classified.xml is None or classified.syntax is None:
            analysis.findings.append(NewFinding("belegfluss", "BF-UNSTRUCTURED", "info"))
            return analysis
        analysis.invoice = read_invoice(classified.xml, classified.syntax)
    except ReadingError as error:
        analysis.findings.append(NewFinding("belegfluss", error.code, "error"))
        return analysis
    analysis.validation = services.validator.validate(classified.xml)
    analysis.findings += _kosit_findings(analysis.validation)
    return analysis


def _find_duplicate(session: Session, document: Document, invoice: InvoiceModel) -> str | None:
    if not invoice.number or not (invoice.seller.vat_id or invoice.seller.name):
        return None
    same_seller = []
    if invoice.seller.vat_id:
        same_seller.append(Invoice.seller_vat_id == invoice.seller.vat_id)
    if invoice.seller.name:
        same_seller.append(Invoice.seller_name == invoice.seller.name)
    other = session.scalars(
        select(Invoice.document_id)
        .where(
            Invoice.org_id == document.org_id,
            Invoice.document_id != document.id,
            Invoice.number == invoice.number,
            or_(*same_seller),
        )
        .limit(1)
    ).first()
    return str(other) if other else None


def _check(session: Session, document: Document, analysis: Analysis) -> None:
    if analysis.invoice is None or analysis.source is None:
        return
    validation = analysis.validation
    reported = {
        term
        for finding in analysis.findings
        if finding.origin == "kosit"
        for term in finding.business_terms
    }
    context = Context(
        source=analysis.source,
        validator_ran=validation is not None and validation.outcome is not Outcome.NOT_PROCESSABLE,
        validator_terms=frozenset(reported),
        pdf_text=analysis.pdf_text,
        duplicate_of=_find_duplicate(session, document, analysis.invoice),
    )
    analysis.findings += [
        NewFinding(
            "belegfluss", f.code, f.severity, business_terms=f.business_terms, params=f.params
        )
        for f in check_invoice(analysis.invoice, context)
    ]


def _status(analysis: Analysis) -> DocumentStatus:
    if analysis.invoice is None or any(f.severity == "error" for f in analysis.findings):
        return DocumentStatus.NEEDS_REVIEW
    return DocumentStatus.READY


def _save(session: Session, document: Document, analysis: Analysis, services: Services) -> None:
    session.execute(delete(Finding).where(Finding.document_id == document.id))
    session.execute(delete(Invoice).where(Invoice.document_id == document.id))
    invoice, validation = analysis.invoice, analysis.validation
    if invoice is not None and analysis.source is not None:
        session.add(
            Invoice(
                document_id=document.id,
                org_id=document.org_id,
                source=analysis.source,
                syntax=analysis.syntax,
                specification_id=invoice.specification_id,
                number=invoice.number,
                issue_date=invoice.issue_date,
                seller_name=invoice.seller.name,
                seller_vat_id=invoice.seller.vat_id,
                currency=invoice.currency,
                net_total=invoice.totals.net,
                vat_total=invoice.totals.vat,
                gross_total=invoice.totals.gross,
                amount_due=invoice.totals.due,
                model=invoice.model_dump(mode="json"),
                pipeline_version=PIPELINE_VERSION,
                validation_outcome=validation.outcome if validation else None,
                validator_engine=validation.engine if validation else None,
                validator_config=services.validator_config if validation else None,
                validator_scenario=validation.scenario if validation else None,
            )
        )
    session.add_all(
        Finding(
            document_id=document.id,
            org_id=document.org_id,
            origin=f.origin,
            code=f.code,
            severity=f.severity,
            message=f.message,
            location=f.location,
            business_terms=list(f.business_terms),
            params=f.params,
        )
        for f in analysis.findings
    )
    document.status = _status(analysis)
    document.status_changed_at = _now()
    document.failure_reason = None
    audit.record(
        session,
        "document.processed",
        org_id=document.org_id,
        actor_user_id=None,
        target_id=document.id,
    )


def process_document(document_id: uuid.UUID, services: Services) -> bool:
    """Process one document. False if there was nothing to do (unknown, locked or done)."""
    with services.session_factory.begin() as session:
        document = session.scalars(
            select(Document).where(Document.id == document_id).with_for_update(skip_locked=True)
        ).one_or_none()
        if document is None or document.status in DONE:
            return False
        document.status = DocumentStatus.PROCESSING
        document.status_changed_at = _now()
        blob_name, media_type = document.blob_name, document.media_type

    analysis = analyse(services.blob_store.read(blob_name), media_type, services)

    with services.session_factory.begin() as session:
        document = session.get_one(Document, document_id, with_for_update=True)
        _check(session, document, analysis)
        _save(session, document, analysis, services)
    return True


def mark_failed(document_id: uuid.UUID, services: Services, reason: str) -> None:
    with services.session_factory.begin() as session:
        document = session.get(Document, document_id, with_for_update=True)
        if document is None or document.status in DONE:
            return
        document.status = DocumentStatus.FAILED
        document.status_changed_at = _now()
        document.failure_reason = reason
        audit.record(
            session,
            "document.failed",
            org_id=document.org_id,
            actor_user_id=None,
            target_id=document.id,
        )
