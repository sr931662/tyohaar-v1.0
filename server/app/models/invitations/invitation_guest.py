"""
InvitationGuest — a single guest entry on an invitation's guest list.

Captures guest identity, RSVP response, delivery status, check-in state,
seating assignment, and dietary preferences. Supports plus-one relationships
and QR-code-based event check-in.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.models.enums import RSVPStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.invitations.invitation import Invitation, InvitationShareChannel


class InvitationDeliveryStatus(str, enum.Enum):
    """
    Delivery state of an invitation sent to a specific guest.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"         # Not yet sent to this guest
    SENT = "sent"               # Dispatch request submitted to the channel provider
    DELIVERED = "delivered"     # Provider confirmed delivery
    FAILED = "failed"           # Provider reported delivery failure
    BOUNCED = "bounced"         # Email bounced or WhatsApp number unreachable
    VIEWED = "viewed"           # Guest opened/viewed the invitation


class InvitationGuest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single guest entry on an invitation.

    One row per guest per invitation. Plus-ones are tracked as separate rows
    with `is_plus_one=True` and `plus_one_of_id` pointing to the primary guest.

    Guest identity:
    - At least one of `email` or `phone` must be present for delivery.
    - `name` is required for the guest list display.

    RSVP flow:
    1. Guest receives invitation (delivery_status=SENT/DELIVERED).
    2. Guest opens invitation (delivery_status=VIEWED, invitation_viewed_at set).
    3. Guest submits RSVP (rsvp_status updated, rsvp_submitted_at set).
    4. Service increments Invitation.total_rsvp_attending / declined counters.

    Check-in flow:
    1. Staff scans `check_in_code` at the venue.
    2. Service validates code, sets attendance_confirmed=True and checked_in_at.

    Seating (`table_number`, `seat_label`) is assigned by the host in the app
    after RSVP collection is complete.

    `dietary_restrictions` is free text to accommodate varied requirements
    without forcing guests into a limited dropdown.
    """

    __tablename__ = "invitation_guests"

    __table_args__ = (
        UniqueConstraint(
            "check_in_code",
            name="uq_invitation_guests_check_in_code",
        ),
        Index("ix_invitation_guests_invitation_id", "invitation_id"),
        Index("ix_invitation_guests_rsvp_status", "invitation_id", "rsvp_status"),
        Index("ix_invitation_guests_plus_one_of_id", "plus_one_of_id"),
        Index("ix_invitation_guests_delivery_status", "invitation_id", "delivery_status"),
        CheckConstraint(
            "plus_ones_allowed >= 0",
            name="ck_invitation_guests_plus_ones_allowed_non_negative",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    invitation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invitations.id", ondelete="CASCADE"),
        nullable=False,
        comment="The invitation this guest belongs to.",
    )

    # ── Guest Identity ────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Full name of the guest as displayed on the invitation and guest list.",
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="Guest's email address for email delivery.",
    )

    phone: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="E.164-formatted phone number for SMS/WhatsApp delivery.",
    )

    # ── RSVP ─────────────────────────────────────────────────────────────────

    rsvp_status: Mapped[RSVPStatus] = mapped_column(
        SAEnum(RSVPStatus, name="rsvp_status", native_enum=False),
        nullable=False,
        default=RSVPStatus.PENDING,
    )

    rsvp_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the guest submitted their RSVP response.",
    )

    rsvp_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional personal message from the guest along with their RSVP.",
    )

    # ── Plus-One Tracking ─────────────────────────────────────────────────────

    is_plus_one: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when this guest was added as a plus-one by a primary invitee.",
    )

    plus_one_of_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invitation_guests.id", ondelete="CASCADE"),
        nullable=True,
        comment="UUID of the primary InvitationGuest who added this person as a plus-one.",
    )

    plus_ones_allowed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="How many plus-ones this guest is permitted to bring.",
    )

    # ── Preferences ───────────────────────────────────────────────────────────

    meal_preference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Meal selection e.g. 'Veg', 'Non-Veg', 'Jain'. Free text.",
    )

    dietary_restrictions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Any dietary restrictions or allergies noted by the guest.",
    )

    # ── Check-In ──────────────────────────────────────────────────────────────

    check_in_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment=(
            "Unique token for QR-code-based venue check-in. "
            "Generated on invitation send. Scan → attendance_confirmed=True."
        ),
    )

    attendance_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True after QR scan or manual confirmation at the venue.",
    )

    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the guest was checked in at the event.",
    )

    # ── Seating ───────────────────────────────────────────────────────────────

    table_number: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Table number assigned by the host after RSVP collection.",
    )

    seat_label: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Seat identifier within the table e.g. 'A3', '5'.",
    )

    # ── Delivery ──────────────────────────────────────────────────────────────

    delivery_channel: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="InvitationShareChannel value used to deliver this invitation.",
    )

    delivery_status: Mapped[InvitationDeliveryStatus] = mapped_column(
        SAEnum(InvitationDeliveryStatus, name="invitation_delivery_status", native_enum=False),
        nullable=False,
        default=InvitationDeliveryStatus.PENDING,
    )

    invitation_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invitation was dispatched to this guest.",
    )

    invitation_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this guest first opened the invitation link.",
    )

    delivery_failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Error details from the delivery provider on failure.",
    )

    # ── Personalisation ───────────────────────────────────────────────────────

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal host note about this guest (not visible to the guest).",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    invitation: Mapped[Invitation] = relationship(
        "Invitation",
        back_populates="guests",
        lazy="noload",
    )

    plus_one_of: Mapped[InvitationGuest | None] = relationship(
        "InvitationGuest",
        remote_side="InvitationGuest.id",
        foreign_keys=[plus_one_of_id],
        lazy="noload",
    )

    @property
    def has_responded(self) -> bool:
        return self.rsvp_status not in (RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE)

    def __repr__(self) -> str:
        return (
            f"<InvitationGuest id={self.id} name={self.name!r} "
            f"rsvp={self.rsvp_status} checked_in={self.attendance_confirmed}>"
        )
