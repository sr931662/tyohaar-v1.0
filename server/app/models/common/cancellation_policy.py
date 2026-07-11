"""
CancellationRefundPolicy — versioned cancellation & refund policy document.

Mirrors the PrivacyPolicy versioning pattern exactly. A new row is inserted
for every material update; superseded rows are kept permanently for audit
purposes. One active (PUBLISHED) row per language at a time.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ContentStatus, Language
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CancellationRefundPolicy(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """A versioned Cancellation & Refund Policy document."""

    __tablename__ = "cancellation_refund_policies"

    __table_args__ = (
        UniqueConstraint(
            "version", "language",
            name="uq_cancellation_policies_version_language",
        ),
        Index("ix_cancellation_policies_status", "status"),
        Index("ix_cancellation_policies_effective_date", "effective_date"),
        Index("ix_cancellation_policies_language", "language"),
    )

    version: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full policy text. Supports HTML/Markdown. Rendered in-app.",
    )

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language", native_enum=False),
        nullable=False,
        default=Language.ENGLISH,
    )

    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", native_enum=False),
        nullable=False,
        default=ContentStatus.DRAFT,
    )

    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    superseded_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cancellation_refund_policies.id", ondelete="SET NULL"),
        nullable=True,
    )

    must_accept_version: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    superseded_by: Mapped[CancellationRefundPolicy | None] = relationship(
        "CancellationRefundPolicy",
        foreign_keys=[superseded_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CancellationRefundPolicy id={self.id} version={self.version!r} "
            f"language={self.language} status={self.status}>"
        )
