"""Users, organisations and membership checks (ADR-0013).

Rule: every route that touches customer data has an `org_id` in its path and depends on
`require_membership`. A non-member gets 404 (not 403), so the existence of other organisations
is not revealed.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from belegfluss import audit
from belegfluss.auth import Principal, current_principal
from belegfluss.db import get_session
from belegfluss.errors import AppError
from belegfluss.models import Membership, Organization, Role, User

PERSONAL_ORG_NAME = "My business"


def _find_user(session: Session, principal: Principal) -> User | None:
    return session.scalars(
        select(User).where(
            User.idp_tenant_id == principal.tenant_id,
            User.idp_object_id == principal.object_id,
        )
    ).one_or_none()


def get_or_create_user(session: Session, principal: Principal) -> User:
    """Return the user for this token; on first sign-in also create a personal organisation."""
    user = _find_user(session, principal)
    if user is not None:
        return user

    user = User(idp_tenant_id=principal.tenant_id, idp_object_id=principal.object_id)
    org = Organization(name=PERSONAL_ORG_NAME)
    session.add_all([user, org])
    session.flush()
    session.add(Membership(org_id=org.id, user_id=user.id, role=Role.OWNER))
    audit.record(session, "user.created", org_id=None, actor_user_id=user.id, target_id=user.id)
    audit.record(session, "org.created", org_id=org.id, actor_user_id=user.id, target_id=org.id)
    try:
        session.commit()
    except IntegrityError:
        # A parallel first request created the user a moment earlier: use that one.
        session.rollback()
        existing = _find_user(session, principal)
        if existing is None:
            raise
        return existing
    return user


def current_user(
    principal: Annotated[Principal, Depends(current_principal)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    return get_or_create_user(session, principal)


def require_membership(
    org_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Membership:
    membership = session.get(Membership, (org_id, user.id))
    if membership is None:
        raise AppError(404, "org.not_found", "Organisation not found.")
    return membership


def memberships_of(session: Session, user: User) -> list[tuple[Membership, Organization]]:
    rows = session.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.org_id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.created_at)
    ).all()
    return [(row[0], row[1]) for row in rows]
