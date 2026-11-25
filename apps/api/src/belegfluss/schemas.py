"""Response models (the API contract, exported to the web app as OpenAPI, see ADR-0011)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from belegfluss.models import DocumentStatus, Role
from belegfluss.reading import InvoiceModel


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Role


class MeOut(BaseModel):
    user_id: uuid.UUID
    organizations: list[OrganizationOut]


class InvoiceSummary(BaseModel):
    """What the list shows about a read invoice."""

    number: str | None
    issue_date: date | None
    seller_name: str | None
    currency: str | None
    gross_total: Decimal | None


class FindingCounts(BaseModel):
    error: int = 0
    warning: int = 0
    info: int = 0


class DocumentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    source: Literal["upload"]
    status: DocumentStatus
    failure_reason: str | None = None
    created_at: datetime
    approved_at: datetime | None = None
    summary: InvoiceSummary | None = None
    finding_counts: FindingCounts = FindingCounts()


class InvoiceOut(BaseModel):
    """A read invoice and which code and validator produced the result."""

    source: Literal["xml", "zugferd", "ai"]
    syntax: Literal["ubl-invoice", "ubl-creditnote", "cii"] | None
    specification_id: str | None
    validation_outcome: Literal["accepted", "rejected", "not_processable", "no_scenario"] | None
    validator_engine: str | None
    validator_config: str | None
    validator_scenario: str | None
    pipeline_version: str
    ai_model: str | None = None
    ai_input_tokens: int | None = None
    ai_output_tokens: int | None = None
    model: InvoiceModel


class FindingOut(BaseModel):
    id: uuid.UUID
    origin: Literal["kosit", "belegfluss"]
    code: str
    severity: Literal["error", "warning", "info"]
    message: (
        str | None
    )  # official rule text (validator findings); our codes are translated in the web app
    location: str | None
    business_terms: list[str]
    params: dict[str, str]


class FieldReviewOut(BaseModel):
    """One correction a person made to an AI-read field."""

    field: str
    before: str | None
    after: str | None
    at: datetime


class DocumentDetailOut(BaseModel):
    document: DocumentOut
    invoice: InvoiceOut | None
    findings: list[FindingOut]
    reviews: list[FieldReviewOut] = []


class ApproveIn(BaseModel):
    acknowledge_errors: bool = False  # required when error findings are still open


class UploadResult(BaseModel):
    document: DocumentOut
    duplicate: bool


class HealthOut(BaseModel):
    status: Literal["ok"]
