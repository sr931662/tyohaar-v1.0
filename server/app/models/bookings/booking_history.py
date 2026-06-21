"""
BookingHistory — append-only audit log of every significant event on a booking.

Distinct from BookingStatusHistory (which records status transitions only).
BookingHistory captures ALL notable events: payments, vendor assignments,
schedule changes, item modifications, admin overrides, and customer actions.
This table drives both the customer-facing booking timeline and the internal
operations audit trail.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
    from app.models.bookings.booking import Booking
    from app.models.users.user import User


class BookingEventType(str, enum.Enum):
    """
    Category of event recorded in BookingHistory.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    STATUS_CHANGED = "status_changed"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    VENDOR_ASSIGNED = "vendor_assigned"
    VENDOR_UNASSIGNED = "vendor_unassigned"
    SCHEDULE_CHANGED = "schedule_changed"
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    ITEM_UPDATED = "item_updated"
    COUPON_APPLIED = "coupon_applied"
    COUPON_REMOVED = "coupon_removed"
    CANCELLATION_REQUESTED = "cancellation_requested"
    RESCHEDULE_REQUESTED = "reschedule_requested"
    RESCHEDULE_APPROVED = "reschedule_approved"
    NOTE_ADDED = "note_added"
    ADMIN_OVERRIDE = "admin_override"
    CUSTOMER_ACTION = "customer_action"
    SYSTEM_EVENT = "system_event"


class BookingActorType(str, enum.Enum):
    """
    Who or what triggered the booking event.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CUSTOMER = "customer"
    VENDOR = "vendor"
    ADMIN = "admin"
    SUPPORT = "support"
    SYSTEM = "system"


class BookingHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single immutable event record in a booking's audit history.

    Rows are APPEND-ONLY and must never be updated or deleted.
    Together with BookingStatusHistory, this forms a complete, searchable
    record of everything that happened to a booking throughout its lifecycle.

    Use cases:
    - Customer-facing booking timeline (filtered by is_customer_visible=True)
    - Admin operations audit trail (all rows)
    - Dispute resolution (who did what and when)
    - Analytics pipeline (event frequency, funnel drop-off, SLA monitoring)

    `old_data` / `new_data` capture before/after snapshots of affected fields.
    Both are NULL for purely informational events (e.g., a document viewed).

    `actor_id` is NULL for system-triggered events (scheduled jobs, webhooks).
    When actor_id is NULL, actor_type must be SYSTEM.

    `context_data` stores event-specific structured metadata:
        PAYMENT_RECEIVED:   {payment_id, amount, gateway, gateway_payment_id}
        VENDOR_ASSIGNED:    {vendor_id, item_id, assignment_id}
        SCHEDULE_CHANGED:   {old_date, new_date, old_time, new_time}
        COUPON_APPLIED:     {coupon_code, discount_amount}
        ADMIN_OVERRIDE:     {reason, override_type, previous_value}
    """

    __tablename__ = "booking_history"

    __table_args__ = (
        Index("ix_booking_history_booking_id", "booking_id"),
        Index("ix_booking_history_event_type", "booking_id", "event_type"),
        Index("ix_booking_history_occurred_at", "booking_id", "occurred_at"),
        Index("ix_booking_history_actor_id", "actor_id"),
        Index("ix_booking_history_visible", "booking_id", "is_customer_visible"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        comment="Booking this event belongs to.",
    )

    # ── Event Classification ──────────────────────────────────────────────────

    event_type: Mapped[BookingEventType] = mapped_column(
        SAEnum(BookingEventType, name="booking_event_type", native_enum=False),
        nullable=False,
        comment="Structured category for filtering, dashboards, and analytics.",
    )

    event_label: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Customer-facing summary line shown in the booking timeline.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal detailed description of what happened and why.",
    )

    # ── Actor ─────────────────────────────────────────────────────────────────

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered this event. NULL for system-generated events.",
    )

    actor_type: Mapped[BookingActorType] = mapped_column(
        SAEnum(BookingActorType, name="booking_actor_type", native_enum=False),
        nullable=False,
        comment="Role of the actor — used for display filtering and access control.",
    )

    # ── Before / After Snapshots ──────────────────────────────────────────────

    old_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot of relevant field values BEFORE this event occurred.",
    )

    new_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot of relevant field values AFTER this event occurred.",
    )

    # ── Context ───────────────────────────────────────────────────────────────

    context_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Event-specific structured metadata: IDs, amounts, reasons, references.",
    )

    is_customer_visible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "False for internal/admin-only events that must NOT appear "
            "in the customer-facing booking timeline."
        ),
    )

    # ── Timestamp ─────────────────────────────────────────────────────────────

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "Authoritative timestamp of when the event occurred. "
            "May differ from created_at for backfilled or async-processed events."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        lazy="noload",
    )

    actor: Mapped[User | None] = relationship(
        "User",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingHistory id={self.id} booking_id={self.booking_id} "
            f"type={self.event_type} actor={self.actor_type} at={self.occurred_at}>"
        )
