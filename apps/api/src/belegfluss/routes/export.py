import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from belegfluss import audit
from belegfluss.db import get_session
from belegfluss.errors import AppError, error_responses
from belegfluss.export import MAX_BYTES, MAX_DOCUMENTS, ExportItem, build_zip
from belegfluss.models import Document, DocumentStatus, Finding, Invoice, Membership
from belegfluss.storage import BlobStore
from belegfluss.tenancy import require_membership

router = APIRouter(prefix="/orgs/{org_id}/export", tags=["export"])


@router.get(
    "",
    response_class=Response,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP with originals + summary.csv",
        },
        **error_responses(401, 403, 404, 413),
    },
)
def export_for_accountant(
    org_id: uuid.UUID,
    request: Request,
    membership: Annotated[Membership, Depends(require_membership)],
    session: Annotated[Session, Depends(get_session)],
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    lang: Literal["de", "en"] = "de",
) -> Response:
    """Approved documents (by invoice date, or upload date if nothing was read) as a ZIP for the
    accountant: originals unchanged plus summary.csv (ADR-0009)."""
    day = func.coalesce(Invoice.issue_date, cast(Document.created_at, Date))
    query = (
        select(Document, Invoice)
        .outerjoin(Invoice, Invoice.document_id == Document.id)
        .where(Document.org_id == org_id, Document.status == DocumentStatus.APPROVED)
        .order_by(day, Document.created_at)
    )
    if from_date:
        query = query.where(day >= from_date)
    if to_date:
        query = query.where(day <= to_date)
    rows = session.execute(query.limit(MAX_DOCUMENTS + 1)).all()
    total_bytes = sum(document.size_bytes for document, _ in rows)
    if len(rows) > MAX_DOCUMENTS or total_bytes > MAX_BYTES:
        raise AppError(413, "export.too_large", "Too many documents: choose a shorter period.")

    open_findings: dict[uuid.UUID, list[str]] = {}
    for document_id, code in session.execute(
        select(Finding.document_id, Finding.code)
        .where(
            Finding.document_id.in_([document.id for document, _ in rows]),
            Finding.severity.in_(["error", "warning"]),
        )
        .order_by(Finding.code)
    ):
        open_findings.setdefault(document_id, []).append(code)

    items = [ExportItem(doc, invoice, open_findings.get(doc.id, [])) for doc, invoice in rows]
    store: BlobStore = request.app.state.blob_store
    content = build_zip(items, store.read, lang)
    audit.record(session, "export.created", org_id=org_id, actor_user_id=membership.user_id)
    session.commit()
    period = f"{from_date or 'start'}_{to_date or 'today'}"
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="belegfluss-export-{period}.zip"'},
    )
