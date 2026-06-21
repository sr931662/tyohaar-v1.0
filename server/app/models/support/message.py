"""
SupportMessage — a single message within a support ticket thread.

Every reply, note, or system event in a support conversation is stored as a
separate SupportMessage row. Append-only by design; editing is tracked via flags,
not row updates. Deletion is logical (is_deleted flag), preserving thread integrity.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List

from sqlalchemy import (
    Boolean,
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.support.ticket import SupportTicket
    from app.models.support.attachment import SupportAttachment


class SupportSenderRole(str, enum.Enum):
    """
    Role of the message author within the support interaction.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CUSTOMER = "customer"    # Customer who raised the ticket
    AGENT = "agent"          # Tyohaar support agent
    ADMIN = "admin"          # Tyohaar admin or supervisor
    SYSTEM = "system"        # Auto-generated system message (status change, SLA alert)


class SupportMessageType(str, enum.Enum):
    """
    Nature of the message content.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    TEXT = "text"              # Standard text reply
    IMAGE = "image"            # Message body is an image reference
    FILE = "file"              # Message body describes an attached file
    SYSTEM = "system"          # Auto-generated status update or event notice
    INTERNAL_NOTE = "internal_note"  # Agent-only note; never shown to customer


class SupportMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single message in a support ticket's conversation thread.

    Append-only design:
    - New messages are only ever INSERTed, never replaced.
    - Editing is tracked via `is_edited` / `edited_at` / `edited_body`. The
      original `body` is preserved for audit; the displayed body switches to
      `edited_body` when `is_edited=True`.
    - Deletion is logical: `is_deleted=True` hides the message from users but
      keeps the row for audit and attachment preservation.

    Internal notes:
    - `is_internal_note=True` (or message_type=INTERNAL_NOTE) marks messages
      visible only to agents and admins. Service layer MUST filter these from
      customer-facing API responses.
    - `sender_role` provides a fast filter for separating customer, agent, and
      system messages without joining to users.

    System messages:
    - `sender_id=NULL` + `sender_role=SYSTEM` for auto-generated events:
      "Ticket escalated to Tier 2", "SLA breach detected", "Booking details attached".

    Delivery tracking:
    - `delivered_at` / `read_at` apply to customer-facing messages from agents
      (indicates the customer received and read the reply).
    """

    __tablename__ = "support_messages"

    __table_args__ = (
        Index("ix_support_messages_ticket_id", "ticket_id"),
        Index("ix_support_messages_ticket_created", "ticket_id", "created_at"),
        Index("ix_support_messages_sender_id", "sender_id"),
        Index("ix_support_messages_is_internal", "ticket_id", "is_internal_note"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Ticket this message belongs to.",
    )

    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who sent this message. NULL for system-generated messages.",
    )

    # ── Classification ────────────────────────────────────────────────────────

    sender_role: Mapped[SupportSenderRole] = mapped_column(
        SAEnum(SupportSenderRole, name="support_sender_role", native_enum=False),
        nullable=False,
        comment="Role of the sender — enables fast filtering without a user join.",
    )

    message_type: Mapped[SupportMessageType] = mapped_column(
        SAEnum(SupportMessageType, name="support_message_type", native_enum=False),
        nullable=False,
        default=SupportMessageType.TEXT,
    )

    # ── Content ───────────────────────────────────────────────────────────────

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Original message body. Preserved immutably for audit. "
            "When is_edited=True, UI should display edited_body instead."
        ),
    )

    edited_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Replacement body after editing. "
            "NULL until the message is edited for the first time."
        ),
    )

    # ── Visibility ────────────────────────────────────────────────────────────

    is_internal_note: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for agent/admin-only notes. "
            "Service layer MUST exclude these from customer-facing API responses."
        ),
    )

    # ── Edit Tracking ─────────────────────────────────────────────────────────

    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the message has been edited after initial send.",
    )

    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent edit.",
    )

    # ── Logical Deletion ──────────────────────────────────────────────────────

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "Logical delete flag. Row is preserved for audit. "
            "UI shows 'This message was deleted.' placeholder when True."
        ),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the message was logically deleted.",
    )

    # ── Delivery ──────────────────────────────────────────────────────────────

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "For agent→customer messages: when the customer's device received the reply. "
            "Set by push/email delivery confirmation."
        ),
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the recipient opened or acknowledged this specific message.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Extensible context: editor user_id for edits, device info for customer messages, "
            "automation rule ID for system messages, translation pairs, etc."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    ticket: Mapped[SupportTicket] = relationship(
        "SupportTicket",
        back_populates="messages",
        lazy="noload",
    )

    sender: Mapped[User | None] = relationship("User", lazy="noload")

    attachments: Mapped[List[SupportAttachment]] = relationship(
        "SupportAttachment",
        back_populates="message",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<SupportMessage id={self.id} ticket_id={self.ticket_id} "
            f"role={self.sender_role} type={self.message_type} deleted={self.is_deleted}>"
        )
