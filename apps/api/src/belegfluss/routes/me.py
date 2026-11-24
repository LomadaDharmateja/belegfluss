from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from belegfluss.db import get_session
from belegfluss.errors import error_responses
from belegfluss.models import Role, User
from belegfluss.schemas import MeOut, OrganizationOut
from belegfluss.tenancy import current_user, memberships_of

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut, responses=error_responses(401, 403))
def get_me(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> MeOut:
    """The signed-in user and their organisations. The first call creates both."""
    orgs = [
        OrganizationOut(id=org.id, name=org.name, role=Role(membership.role))
        for membership, org in memberships_of(session, user)
    ]
    return MeOut(user_id=user.id, organizations=orgs)
