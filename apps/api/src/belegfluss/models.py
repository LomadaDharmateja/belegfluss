"""Database tables. Every table with customer data carries org_id (see ADR-0013)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"
    ACCOUNTANT = "accountant"


class DocumentStatus(StrEnum):
    RECEIVED = "received"  # stored, waiting for the worker
    PROCESSING = "processing"
    READY = "ready"  # read and checked, no errors
    NEEDS_REVIEW = "needs_review"  # errors found, or nothing could be read automatically
    FAILED = "failed"  # processing gave up after retries; `failure_reason` says why


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """A person who signs in. Only identity-provider IDs are stored (data minimisation)."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("idp_tenant_id", "idp_object_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idp_tenant_id: Mapped[str] = mapped_column(String(64))  # token claim "tid"
    idp_object_id: Mapped[str] = mapped_column(String(64))  # token claim "oid"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(20))


class Document(Base):
    """An uploaded original file. The bytes live in Blob storage, keyed by SHA-256."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("org_id", "sha256"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    sha256: Mapped[str] = mapped_column(String(64))
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    original_filename: Mapped[str] = mapped_column(String(255))
    blob_name: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(20), default="upload")
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.RECEIVED)
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    failure_reason: Mapped[str | None] = mapped_column(String(64))  # stable code, not free text
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    """Append-only log of actions. Holds IDs and action names only, never invoice content."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[uuid.UUID | None]
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    """What was read from a document (ADR-0015): summary columns + the full model as JSONB.

    Derived data: re-processing replaces it, and `pipeline_version` says which code produced it.
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(20))  # xml | zugferd
    syntax: Mapped[str | None] = mapped_column(String(20))  # ubl-invoice | ubl-creditnote | cii
    specification_id: Mapped[str | None] = mapped_column(String(300))  # BT-24
    number: Mapped[str | None] = mapped_column(String(200))  # BT-1
    issue_date: Mapped[date | None] = mapped_column(Date)  # BT-2
    seller_name: Mapped[str | None] = mapped_column(String(300))  # BT-27
    seller_vat_id: Mapped[str | None] = mapped_column(String(50))  # BT-31
    currency: Mapped[str | None] = mapped_column(String(3))  # BT-5
    net_total: Mapped[Decimal | None] = mapped_column(Numeric)  # BT-109
    vat_total: Mapped[Decimal | None] = mapped_column(Numeric)  # BT-110
    gross_total: Mapped[Decimal | None] = mapped_column(Numeric)  # BT-112
    amount_due: Mapped[Decimal | None] = mapped_column(Numeric)  # BT-115
    model: Mapped[dict[str, Any]] = mapped_column(JSONB)
    pipeline_version: Mapped[str] = mapped_column(String(40))
    validation_outcome: Mapped[str | None] = mapped_column(String(20))
    validator_engine: Mapped[str | None] = mapped_column(String(100))
    validator_config: Mapped[str | None] = mapped_column(String(100))
    validator_scenario: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Finding(Base):
    """A problem or hint about a document: from the official validator ("kosit") or our checks."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    origin: Mapped[str] = mapped_column(String(20))  # kosit | belegfluss
    code: Mapped[str] = mapped_column(String(64))  # e.g. BR-CO-15, BF-VAT-RATE-UNUSUAL
    severity: Mapped[str] = mapped_column(String(10))  # error | warning | info
    message: Mapped[str | None] = mapped_column(Text)  # official rule text (kosit only)
    location: Mapped[str | None] = mapped_column(Text)  # XPath in the source XML
    business_terms: Mapped[list[str]] = mapped_column(ARRAY(String(12)), default=list)
    params: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)  # values for the message
