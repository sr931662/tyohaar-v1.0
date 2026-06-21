"""
SupportTicket — the root aggregate for a customer support case.

A ticket is a threaded conversation: one ticket → many messages → many attachments.
Never flatten messages into a single JSONB column; keep them in support_messages.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.models.mixins import NotesMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.bookings.booking import Booking
    from app.models.payments.payment import Payment
    from app.models.support.message import SupportMessage
    from app.models.support.attachment import SupportAttachment


class SupportTicket(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, Base):
    """
    A customer support case managed as a threaded conversation.

    Structure:
        SupportTicket (1)
          └── SupportMessage (N) — every reply, note, and system event
                └── SupportAttachment (N) — files linked to a specific message

    Attachments can also be linked directly to the ticket (message_id=NULL)
    for files uploaded at case creation before any message exists.

    Ticket number:
    `ticket_number` is a human-readable, sequential identifier (e.g., TKT-2024-001234)
    shown to customers. UNIQUE constraint enforced at DB level.

    Context links:
    `booking_id` and `payment_id` are nullable FKs allowing the ticket to be
    directly associated with a specific booking or payment. This enables the
    support dashboard to surface relevant order details inline without a text search.

    SLA:
    `sla_due_at` stores the response-due timestamp computed from the ticket's
    priority and creation time according to the configured SLA policy.
    The support service sets this on ticket creation; a background job monitors
    breaches and escalates or alerts as needed.

    `first_response_at` is set on the first agent/admin reply (not system messages).
    It drives SLA compliance reporting (First Response Time metric).

    `last_activity_at` is denormalized — updated on every new message insert —
    for fast sorting of ticket lists by recency without a subquery on messages.

    Escalation:
    `reopened_count` tracks how many times this ticket has been reopened after
    RESOLVED or CLOSED, a key quality metric.

    `internal_notes` (from NotesMixin) holds agent memos not visible to customers.
    """

    __tablename__ = "support_tickets"

    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_support_tickets_ticket_number"),
        Index("ix_support_tickets_customer_id", "customer_id"),
        Index("ix_support_tickets_assigned_agent_id", "assigned_agent_id"),
        Index("ix_support_tickets_status", "ticket_status"),
        Index("ix_support_tickets_priority", "priority"),
        Index("ix_support_tickets_booking_id", "booking_id"),
        Index("ix_support_tickets_payment_id", "payment_id"),
        Index("ix_support_tickets_sla_due", "sla_due_at"),
        Index("ix_support_tickets_last_activity", "last_activity_at"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    ticket_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Human-readable unique identifier shown to customers. e.g. TKT-2024-001234.",
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Customer who raised this support case.",
    )

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Support agent currently handling this ticket. NULL = unassigned.",
    )

    # ── Context Links ─────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related booking, if the issue is booking-specific.",
    )

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related payment, if the issue concerns a specific transaction.",
    )

    # ── Classification ────────────────────────────────────────────────────────

    category: Mapped[TicketCategory] = mapped_column(
        SAEnum(TicketCategory, name="ticket_category", native_enum=False),
        nullable=False,
    )

    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority", native_enum=False),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )

    ticket_status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", native_enum=False),
        nullable=False,
        default=TicketStatus.OPEN,
    )

    # ── Content ───────────────────────────────────────────────────────────────

    subject: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="One-line summary of the issue shown in ticket list views.",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Customer's initial problem description submitted at ticket creation. "
            "Also stored as the first SupportMessage for thread continuity."
        ),
    )

    resolution_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Agent-written summary of how the issue was resolved. "
            "Shown to the customer when the ticket is marked RESOLVED."
        ),
    )

    # ── SLA & Response Timestamps ─────────────────────────────────────────────

    sla_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "SLA response deadline computed from priority + creation time. "
            "Monitored by background jobs for breach detection and escalation."
        ),
    )

    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Timestamp of the first agent or admin reply (not system messages). "
            "Key SLA metric: First Response Time = first_response_at - created_at."
        ),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When ticket_status transitioned to RESOLVED.",
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When ticket_status transitioned to CLOSED (after resolution confirmation).",
    )

    # ── Activity ──────────────────────────────────────────────────────────────

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Denormalized timestamp of the most recent message. "
            "Updated on every new SupportMessage insert for fast sort."
        ),
    )

    reopened_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Number of times this ticket was reopened after RESOLVED or CLOSED.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped[User] = relationship(
        "User",
        foreign_keys=[customer_id],
        lazy="noload",
    )

    assigned_agent: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_agent_id],
        lazy="noload",
    )

    booking: Mapped[Booking | None] = relationship("Booking", lazy="noload")

    payment: Mapped[Payment | None] = relationship("Payment", lazy="noload")

    messages: Mapped[List[SupportMessage]] = relationship(
        "SupportMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="SupportMessage.created_at",
    )

    attachments: Mapped[List[SupportAttachment]] = relationship(
        "SupportAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<SupportTicket id={self.id} number={self.ticket_number!r} "
            f"status={self.ticket_status} priority={self.priority}>"
        )
