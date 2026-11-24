import logging
import uuid
from typing import Annotated

from azure.core.exceptions import AzureError
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from belegfluss import audit
from belegfluss.db import get_session
from belegfluss.errors import AppError, error_responses
from belegfluss.models import Document, Finding, Invoice, Membership
from belegfluss.queue import DocumentQueue
from belegfluss.schemas import (
    DocumentDetailOut,
    DocumentOut,
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


@router.get(
    "/{document_id}", response_model=DocumentDetailOut, responses=error_responses(401, 403, 404)
)
def get_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    _membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentDetailOut:
    """One document with the invoice read from it and all findings (errors first)."""
    doc = session.scalars(
        select(Document).where(Document.org_id == org_id, Document.id == document_id)
    ).one_or_none()
    if doc is None:
        raise AppError(404, "document.not_found", "Document not found.")
    invoice = session.scalars(select(Invoice).where(Invoice.document_id == doc.id)).one_or_none()
    findings = session.scalars(
        select(Finding).where(Finding.document_id == doc.id).order_by(_SEVERITY_ORDER, Finding.code)
    ).all()
    counts = FindingCounts()
    for finding in findings:
        setattr(counts, finding.severity, getattr(counts, finding.severity) + 1)
    return DocumentDetailOut(
        document=_to_out(doc, invoice, counts),
        invoice=InvoiceOut.model_validate(invoice, from_attributes=True) if invoice else None,
        findings=[FindingOut.model_validate(f, from_attributes=True) for f in findings],
    )


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
