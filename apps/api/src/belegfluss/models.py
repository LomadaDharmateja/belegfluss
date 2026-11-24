"""Database tables. Every table with customer data carries org_id (see ADR-0013)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"
    ACCOUNTANT = "accountant"


class DocumentStatus(StrEnum):
    RECEIVED = "received"


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
