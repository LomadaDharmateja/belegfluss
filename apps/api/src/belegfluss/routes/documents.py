import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from belegfluss import audit
from belegfluss.db import get_session
from belegfluss.errors import AppError, error_responses
from belegfluss.models import Document, Membership
from belegfluss.schemas import DocumentOut, UploadResult
from belegfluss.settings import Settings
from belegfluss.storage import BlobStore
from belegfluss.tenancy import require_membership
from belegfluss.uploads import check_upload, safe_filename

router = APIRouter(prefix="/orgs/{org_id}/documents", tags=["documents"])

# Multipart overhead allowed on top of the file size before the request is rejected early.
_MULTIPART_OVERHEAD = 64 * 1024


def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut.model_validate(doc, from_attributes=True)


@router.get("", response_model=list[DocumentOut], responses=error_responses(401, 403, 404))
def list_documents(
    org_id: uuid.UUID,
    _membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> list[DocumentOut]:
    """Documents of one organisation, newest first."""
    docs = session.scalars(
        select(Document).where(Document.org_id == org_id).order_by(Document.created_at.desc())
    ).all()
    return [_to_out(doc) for doc in docs]


@router.get("/{document_id}", response_model=DocumentOut, responses=error_responses(401, 403, 404))
def get_document(
    org_id: uuid.UUID,
    document_id: uuid.UUID,
    _membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentOut:
    doc = session.scalars(
        select(Document).where(Document.org_id == org_id, Document.id == document_id)
    ).one_or_none()
    if doc is None:
        raise AppError(404, "document.not_found", "Document not found.")
    return _to_out(doc)


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
    return UploadResult(document=_to_out(doc), duplicate=False)
