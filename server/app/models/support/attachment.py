"""
SupportAttachment — a file uploaded within a support ticket thread.

Every attachment belongs to a ticket and optionally to a specific message.
Attachments survive message deletion (message_id is SET NULL on message delete).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MediaType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.support.ticket import SupportTicket
    from app.models.support.message import SupportMessage


class VirusScanStatus(str, enum.Enum):
    """
    Outcome of the antivirus scan run against an uploaded file.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"        # Scan not yet started
    SCANNING = "scanning"      # Scan in progress
    CLEAN = "clean"            # No threats found; file is safe to serve
    INFECTED = "infected"      # Threat detected; file quarantined, must not be served
    SKIPPED = "skipped"        # File type or size excluded from scan policy
    FAILED = "failed"          # Scanner error; treat as PENDING for retry


class SupportAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A file attached to a support ticket, optionally linked to a specific message.

    Ownership:
    - `ticket_id` is always set (NOT NULL). The attachment is owned by the ticket.
    - `message_id` is nullable. When a customer or agent attaches a file while
      composing a message, message_id is set. Files uploaded at ticket creation
      time (before any message exists) have message_id=NULL.
    - When a message is soft-deleted or hard-deleted, `message_id` is SET NULL.
      The attachment is NOT deleted — it remains on the ticket for audit purposes.

    Storage:
    - `storage_key` is the cloud storage object key (S3 key, GCS path).
    - `storage_url` is the pre-signed or CDN URL for serving. URLs may expire;
      the service layer re-generates them as needed from storage_key.
    - `thumbnail_url` is a resized preview for images and video thumbnails.

    Security:
    - `virus_scan_status` must be CLEAN before the file is served to any user.
    - `checksum` (SHA-256) enables integrity verification and deduplication.
    - Files with virus_scan_status=INFECTED must never be served; flag the ticket.

    `file_size_bytes` uses BigInteger to support files up to ~9.2 EB (more than
    sufficient; practical limit is enforced in the upload service layer).
    """

    __tablename__ = "support_attachments"

    __table_args__ = (
        Index("ix_support_attachments_ticket_id", "ticket_id"),
        Index("ix_support_attachments_message_id", "message_id"),
        Index("ix_support_attachments_uploaded_by_id", "uploaded_by_id"),
        Index("ix_support_attachments_virus_scan", "virus_scan_status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        comment="Ticket this attachment belongs to. Always set.",
    )

    message_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_messages.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Message this file was attached to. NULL for files uploaded at ticket "
            "creation or after message deletion."
        ),
    )

    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who uploaded this file (customer or agent).",
    )

    # ── File Classification ───────────────────────────────────────────────────

    media_type: Mapped[MediaType] = mapped_column(
        SAEnum(MediaType, name="media_type", native_enum=False),
        nullable=False,
        comment="High-level media type: IMAGE, VIDEO, DOCUMENT, AUDIO.",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="IANA MIME type e.g. 'image/jpeg', 'application/pdf', 'video/mp4'.",
    )

    # ── File Identity ─────────────────────────────────────────────────────────

    filename: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Original filename as provided by the uploader, sanitized for display.",
    )

    # ── Storage ───────────────────────────────────────────────────────────────

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment=(
            "Cloud storage object key (S3 key or GCS path). "
            "Permanent identifier; use to re-generate pre-signed URLs."
        ),
    )

    storage_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment=(
            "Pre-signed or CDN URL for serving the file. "
            "May expire; regenerate from storage_key as needed."
        ),
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Resized preview URL for images, or poster frame URL for videos.",
    )

    # ── File Properties ───────────────────────────────────────────────────────

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes. BigInteger supports files up to ~9.2 EB.",
    )

    checksum: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="SHA-256 hex digest for integrity verification and deduplication.",
    )

    # ── Security ──────────────────────────────────────────────────────────────

    virus_scan_status: Mapped[VirusScanStatus] = mapped_column(
        SAEnum(VirusScanStatus, name="virus_scan_status", native_enum=False),
        nullable=False,
        default=VirusScanStatus.PENDING,
        comment=(
            "Antivirus scan result. File must be CLEAN before serving. "
            "INFECTED files are quarantined and must not be made accessible."
        ),
    )

    virus_scan_result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Raw scanner output or threat name if INFECTED.",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exact timestamp when the upload completed.",
    )

    # ── Extensibility ─────────────────────────────────────────────────────────

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Flexible context: image dimensions, video duration, page count for PDFs, "
            "OCR extraction results, accessibility alt-text, etc."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    ticket: Mapped[SupportTicket] = relationship(
        "SupportTicket",
        back_populates="attachments",
        lazy="noload",
    )

    message: Mapped[SupportMessage | None] = relationship(
        "SupportMessage",
        back_populates="attachments",
        lazy="noload",
    )

    uploaded_by: Mapped[User | None] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<SupportAttachment id={self.id} ticket_id={self.ticket_id} "
            f"filename={self.filename!r} scan={self.virus_scan_status}>"
        )
