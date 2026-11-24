"""Response models (the API contract, exported to the web app as OpenAPI, see ADR-0011)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from belegfluss.models import DocumentStatus, Role


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Role


class MeOut(BaseModel):
    user_id: uuid.UUID
    organizations: list[OrganizationOut]


class DocumentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    source: Literal["upload"]
    status: DocumentStatus
    created_at: datetime


class UploadResult(BaseModel):
    document: DocumentOut
    duplicate: bool


class HealthOut(BaseModel):
    status: Literal["ok"]
