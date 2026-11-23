"""Write audit events. Only IDs and action names, never file names or invoice content."""

import uuid

from sqlalchemy.orm import Session

from belegfluss.models import AuditEvent


def record(
    session: Session,
    action: str,
    *,
    org_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    target_id: uuid.UUID | None = None,
) -> None:
    """Add an audit event to the current transaction (committed together with the change)."""
    session.add(
        AuditEvent(org_id=org_id, actor_user_id=actor_user_id, action=action, target_id=target_id)
    )
