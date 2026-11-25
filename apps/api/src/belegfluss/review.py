"""Human review (ADR-0017): correct AI-read fields, approve, reopen.

- Only AI-read invoices can be corrected: for XML and ZUGFeRD the XML is legally leading (F15).
- Every change is stored in `field_reviews` (before/after). The audit log gets the action only.
- After a correction the code checks run again (no AI call, no validator).
- Approving with open errors needs an explicit acknowledgement; it is audited separately.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from belegfluss import audit
from belegfluss.checks import CheckFinding, Context, check_invoice
from belegfluss.errors import AppError
from belegfluss.extraction.verify import check_formats
from belegfluss.models import Document, DocumentStatus, FieldReview, Finding, Invoice
from belegfluss.pipeline import find_duplicate
from belegfluss.reading import InvoiceModel, Source


class InvoiceCorrection(BaseModel):
    """Fields a person may correct. Only the fields sent are changed; null clears a value."""

    model_config = ConfigDict(extra="forbid")

    number: str | None = Field(default=None, max_length=200)
    issue_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    seller_name: str | None = Field(default=None, max_length=300)
    seller_vat_id: str | None = Field(default=None, max_length=50)
    iban: str | None = Field(default=None, max_length=50)
    net: Decimal | None = None
    vat: Decimal | None = None
    gross: Decimal | None = None
    due: Decimal | None = None


# Field -> business term, for the presence findings that a correction resolves.
FIELD_TERMS = {
    "number": "BT-1",
    "issue_date": "BT-2",
    "due_date": "BT-9",
    "currency": "BT-5",
    "seller_name": "BT-27",
    "seller_vat_id": "BT-31",
    "iban": "BT-84",
    "net": "BT-109",
    "vat": "BT-110",
    "gross": "BT-112",
    "due": "BT-115",
}
# Presence findings name their field differently (verify.check_presence).
_PRESENCE_FIELD = {"number": "number", "seller_vat_id": "vat_id", "iban": "iban", "gross": "gross"}


@dataclass(frozen=True)
class Change:
    field: str
    before: str | None
    after: str | None


def _get(model: InvoiceModel, name: str) -> object:
    match name:
        case "seller_name":
            return model.seller.name
        case "seller_vat_id":
            return model.seller.vat_id
        case "iban":
            return model.ibans[0] if model.ibans else None
        case "net" | "vat" | "gross" | "due":
            return getattr(model.totals, name)
        case _:
            return getattr(model, name)


def _set(model: InvoiceModel, name: str, value: object) -> None:
    match name:
        case "seller_name":
            model.seller.name = value  # type: ignore[assignment]
        case "seller_vat_id":
            model.seller.vat_id = value  # type: ignore[assignment]
        case "iban":
            model.ibans = ([str(value)] if value else []) + model.ibans[1:]
        case "net" | "vat" | "gross" | "due":
            setattr(model.totals, name, value)
        case _:
            setattr(model, name, value)


def _as_text(value: object) -> str | None:
    return None if value is None else str(value)


def apply_correction(
    model: InvoiceModel, correction: InvoiceCorrection
) -> tuple[InvoiceModel, list[Change]]:
    corrected = model.model_copy(deep=True)
    changes = []
    for name in sorted(correction.model_fields_set):
        before, after = _get(corrected, name), getattr(correction, name)
        if before == after:
            continue
        _set(corrected, name, after)
        changes.append(Change(name, _as_text(before), _as_text(after)))
    return InvoiceModel.model_validate(corrected.model_dump()), changes


def _sync_summary(invoice: Invoice, model: InvoiceModel) -> None:
    invoice.model = model.model_dump(mode="json")
    invoice.number = model.number
    invoice.issue_date = model.issue_date
    invoice.seller_name = model.seller.name
    invoice.seller_vat_id = model.seller.vat_id
    invoice.currency = model.currency
    invoice.net_total = model.totals.net
    invoice.vat_total = model.totals.vat
    invoice.gross_total = model.totals.gross
    invoice.amount_due = model.totals.due


def _recheck(session: Session, document: Document, model: InvoiceModel, changed: set[str]) -> None:
    """Replace the code findings. Kept: the AI marker, and presence findings for fields nobody
    corrected (those can't be re-checked without the document's text layer)."""
    corrected_presence = {_PRESENCE_FIELD[name] for name in changed if name in _PRESENCE_FIELD}
    kept = []
    for finding in session.scalars(
        select(Finding).where(Finding.document_id == document.id, Finding.origin == "belegfluss")
    ):
        if finding.code == "BF-AI-READ" or (
            finding.code == "BF-AI-NOT-IN-DOCUMENT"
            and finding.params.get("field") not in corrected_presence
        ):
            kept.append(finding.id)
    session.execute(
        delete(Finding).where(
            Finding.document_id == document.id,
            Finding.origin == "belegfluss",
            Finding.id.not_in(kept),
        )
    )
    context = Context(
        source=Source.AI,
        validator_ran=False,
        duplicate_of=find_duplicate(session, document, model),
    )
    new: list[CheckFinding] = check_invoice(model, context) + check_formats(
        model, datetime.now(UTC).date()
    )
    session.add_all(
        Finding(
            document_id=document.id,
            org_id=document.org_id,
            origin="belegfluss",
            code=f.code,
            severity=f.severity,
            business_terms=list(f.business_terms),
            params=f.params,
        )
        for f in new
    )


def correct_invoice(
    session: Session, document: Document, correction: InvoiceCorrection, user_id: uuid.UUID
) -> list[Change]:
    if document.status == DocumentStatus.APPROVED:
        raise AppError(409, "document.approved", "Reopen the document before changing it.")
    invoice = session.scalars(
        select(Invoice).where(Invoice.document_id == document.id)
    ).one_or_none()
    if invoice is None or invoice.source != "ai":
        raise AppError(409, "invoice.not_editable", "Only AI-read invoices can be corrected.")
    model, changes = apply_correction(InvoiceModel.model_validate(invoice.model), correction)
    if not changes:
        return []
    _sync_summary(invoice, model)
    session.add_all(
        FieldReview(
            document_id=document.id,
            org_id=document.org_id,
            field=change.field,
            before=change.before,
            after=change.after,
            reviewed_by=user_id,
        )
        for change in changes
    )
    _recheck(session, document, model, {change.field for change in changes})
    audit.record(
        session,
        "invoice.corrected",
        org_id=document.org_id,
        actor_user_id=user_id,
        target_id=document.id,
    )
    return changes


def approve(
    session: Session, document: Document, user_id: uuid.UUID, *, acknowledge_errors: bool
) -> None:
    if document.status == DocumentStatus.APPROVED:
        return
    if document.status not in (DocumentStatus.READY, DocumentStatus.NEEDS_REVIEW):
        raise AppError(409, "document.not_ready", "The document hasn't been checked yet.")
    has_errors = (
        session.scalars(
            select(Finding.id).where(
                Finding.document_id == document.id, Finding.severity == "error"
            )
        ).first()
        is not None
    )
    if has_errors and not acknowledge_errors:
        raise AppError(409, "document.has_errors", "Confirm that you have seen the errors.")
    document.status = DocumentStatus.APPROVED
    document.status_changed_at = document.approved_at = datetime.now(UTC)
    document.approved_by = user_id
    action = "document.approved_with_errors" if has_errors else "document.approved"
    audit.record(
        session, action, org_id=document.org_id, actor_user_id=user_id, target_id=document.id
    )


def reopen(session: Session, document: Document, user_id: uuid.UUID) -> None:
    if document.status != DocumentStatus.APPROVED:
        return
    document.status = DocumentStatus.NEEDS_REVIEW
    document.status_changed_at = datetime.now(UTC)
    document.approved_at = document.approved_by = None
    audit.record(
        session,
        "document.reopened",
        org_id=document.org_id,
        actor_user_id=user_id,
        target_id=document.id,
    )
