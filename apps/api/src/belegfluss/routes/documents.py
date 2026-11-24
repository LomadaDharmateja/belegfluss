import logging
import uuid
from typing import Annotated

from azure.core.exceptions import AzureError
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from belegfluss import audit, review
from belegfluss.db import get_session
from belegfluss.errors import AppError, error_responses
from belegfluss.models import Document, FieldReview, Finding, Invoice, Membership
from belegfluss.queue import DocumentQueue
from belegfluss.review import InvoiceCorrection
from belegfluss.schemas import (
    ApproveIn,
    DocumentDetailOut,
    DocumentOut,
    FieldReviewOut,
    FindingCounts,
    FindingOut,
    InvoiceOut,
    InvoiceSummary,
    UploadResult,
)
from belegfluss.settings import Settings
from belegfluss.storage import BlobStore
from belegfluss.tenancy import require_membership
from belegfluss.uploads import check_upload, safe_filename

router = APIRouter(prefix="/orgs/{org_id}/documents", tags=["documents"])
logger = logging.getLogger(__name__)

# Multipart overhead allowed on top of the file size before the request is rejected early.
_MULTIPART_OVERHEAD = 64 * 1024


def _to_out(
    doc: Document, invoice: Invoice | None = None, counts: FindingCounts | None = None
) -> DocumentOut:
    out = DocumentOut.model_validate(doc, from_attributes=True)
    if invoice is not None:
        out.summary = InvoiceSummary.model_validate(invoice, from_attributes=True)
    out.finding_counts = counts or FindingCounts()
    return out


@router.get("", response_model=list[DocumentOut], responses=error_responses(401, 403, 404))
def list_documents(
    org_id: uuid.UUID,
    _membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> list[DocumentOut]:
    """Documents of one organisation, newest first, with what was read and how many findings."""
    docs = session.scalars(
        select(Document).where(Document.org_id == org_id).order_by(Document.created_at.desc())
    ).all()
    ids = [doc.id for doc in docs]
    invoices = {
        invoice.document_id: invoice
        for invoice in session.scalars(select(Invoice).where(Invoice.document_id.in_(ids)))
    }
    counts: dict[uuid.UUID, FindingCounts] = {}
    for document_id, severity, count in session.execute(
        select(Finding.document_id, Finding.severity, func.count())
        .where(Finding.document_id.in_(ids))
        .group_by(Finding.document_id, Finding.severity)
    ):
        setattr(counts.setdefault(document_id, FindingCounts()), severity, count)
    return [_to_out(doc, invoices.get(doc.id), counts.get(doc.id)) for doc in docs]


_SEVERITY_ORDER = case({"error": 0, "warning": 1}, value=Finding.severity, else_=2)


def _find_document(session: Session, org_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    doc = session.scalars(
        select(Document).where(Document.org_id == org_id, Document.id == document_id)
    ).one_or_none()
    if doc is None:
        raise AppError(404, "document.not_found", "Document not found.")
    return doc


def _detail(session: Session, doc: Document) -> DocumentDetailOut:
    invoice = session.scalars(select(Invoice).where(Invoice.document_id == doc.id)).one_or_none()
    findings = session.scalars(
        select(Finding).where(Finding.document_id == doc.id).order_by(_SEVERITY_ORDER, Finding.code)
    ).all()
    reviews = session.scalars(
        select(FieldReview).where(FieldReview.document_id == doc.id).order_by(FieldReview.at)
    ).all()
    counts = FindingCounts()
    for finding in findings:
        setattr(counts, finding.severity, getattr(counts, finding.severity) + 1)
    return DocumentDetailOut(
        document=_to_out(doc, invoice, counts),
        invoice=InvoiceOut.model_validate(invoice, from_attributes=True) if invoice else None,
        findings=[FindingOut.model_validate(f, from_attributes=True) for f in findings],
        reviews=[FieldReviewOut.model_validate(r, from_attributes=True) for r in reviews],
    )


@router.get(
    "/{document_id}", response_model=DocumentDetailOut, responses=error_responses(401, 403, 404)
)
def get_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    _membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentDetailOut:
    """One document with the invoice read from it, all findings (errors first) and corrections."""
    return _detail(session, _find_document(session, org_id, document_id))


@router.post(
    "",
    response_model=UploadResult,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": UploadResult, "description": "Exact duplicate of an existing document"},
        **error_responses(400, 401, 403, 404, 413, 415),
    },
)
def upload_document(
    org_id: uuid.UUID,
    request: Request,
    response: Response,
    file: Annotated[UploadFile, File(description="PDF, XML, PNG or JPEG")],
    membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> UploadResult:
    """Store an original file unchanged. Uploading the same bytes again returns the existing one."""
    settings: Settings = request.app.state.settings
    content_length = int(request.headers.get("content-length") or 0)
    if content_length > settings.max_upload_bytes + _MULTIPART_OVERHEAD:
        raise AppError(413, "upload.too_large", "File is too large.")

    checked = check_upload(file.file, settings.max_upload_bytes)

    existing = session.scalars(
        select(Document).where(Document.org_id == org_id, Document.sha256 == checked.sha256)
    ).one_or_none()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return UploadResult(document=_to_out(existing), duplicate=True)

    store: BlobStore = request.app.state.blob_store
    blob_name = store.put_original(org_id, checked.sha256, file.file, checked.media_type)
    doc = Document(
        org_id=org_id,
        sha256=checked.sha256,
        media_type=checked.media_type,
        size_bytes=checked.size_bytes,
        original_filename=safe_filename(file.filename),
        blob_name=blob_name,
        uploaded_by=membership.user_id,
    )
    session.add(doc)
    try:
        session.flush()
    except IntegrityError:
        # The same file was uploaded in parallel and won the race: report it as a duplicate.
        session.rollback()
        winner = session.scalars(
            select(Document).where(Document.org_id == org_id, Document.sha256 == checked.sha256)
        ).one()
        response.status_code = status.HTTP_200_OK
        return UploadResult(document=_to_out(winner), duplicate=True)
    audit.record(
        session,
        "document.uploaded",
        org_id=org_id,
        actor_user_id=membership.user_id,
        target_id=doc.id,
    )
    session.commit()
    _enqueue(request.app.state.queue, doc.id)
    return UploadResult(document=_to_out(doc), duplicate=False)


def _enqueue(queue: DocumentQueue, document_id: uuid.UUID) -> None:
    """Ask the worker to process the document. If this fails, the sweeper picks it up later."""
    try:
        queue.send(document_id)
    except AzureError as exc:
        logger.warning("document %s: enqueue failed (%s)", document_id, type(exc).__name__)


@router.patch(
    "/{document_id}/invoice",
    response_model=DocumentDetailOut,
    responses=error_responses(401, 403, 404, 409, 422),
)
def correct_invoice(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    correction: InvoiceCorrection,
    membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentDetailOut:
    """Correct fields of an AI-read invoice. Only the fields sent change (ADR-0017)."""
    doc = _find_document(session, org_id, document_id)
    review.correct_invoice(session, doc, correction, membership.user_id)
    session.commit()
    return _detail(session, doc)


@router.post(
    "/{document_id}/approve",
    response_model=DocumentDetailOut,
    responses=error_responses(401, 403, 404, 409),
)
def approve_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    body: ApproveIn,
    membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentDetailOut:
    """Approve for the accountant. With open errors, `acknowledge_errors` must be true."""
    doc = _find_document(session, org_id, document_id)
    review.approve(session, doc, membership.user_id, acknowledge_errors=body.acknowledge_errors)
    session.commit()
    return _detail(session, doc)


@router.post(
    "/{document_id}/reopen",
    response_model=DocumentDetailOut,
    responses=error_responses(401, 403, 404),
)
def reopen_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentDetailOut:
    """Undo an approval, e.g. to correct a field."""
    doc = _find_document(session, org_id, document_id)
    review.reopen(session, doc, membership.user_id)
    session.commit()
    return _detail(session, doc)
