"""
CelebrationGuest — guest record for a celebration with RSVP and check-in tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
from app.models.enums import RSVPStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration
    from app.models.users.user import User


class CelebrationGuest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A guest invited to a Celebration.

    If the guest is a registered Tyohaar user, `user_id` links to their account.
    Otherwise name/phone/email are stored directly for external guests.

    `group_tag` allows informal grouping (e.g. 'Family', 'Office', 'School Friends').

    RSVP flow: guest receives invitation → responds → `rsvp_status` is updated.
    `checked_in_at` is set when the guest is physically checked in at the event.

    The UNIQUE constraint on (celebration_id, user_id) prevents adding the same
    registered user twice to the same celebration.
    """

    __tablename__ = "celebration_guests"

    __table_args__ = (
        UniqueConstraint(
            "celebration_id",
            "user_id",
            name="uq_celebration_guests_celebration_user",
        ),
        Index("ix_celebration_guests_celebration_id", "celebration_id"),
        Index("ix_celebration_guests_user_id", "user_id"),
        Index("ix_celebration_guests_rsvp", "celebration_id", "rsvp_status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Guest Identity ────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Set if guest is a registered Tyohaar user. NULL for external guests.",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Guest's display name (copied from user profile if user_id is set)",
    )

    phone: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="E.164 format for SMS/WhatsApp invitation delivery",
    )

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # ── Grouping ──────────────────────────────────────────────────────────────

    group_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Informal group label (e.g. 'Family', 'Colleagues', 'School Friends')",
    )

    # ── RSVP ──────────────────────────────────────────────────────────────────

    rsvp_status: Mapped[RSVPStatus] = mapped_column(
        SAEnum(RSVPStatus, name="rsvp_status", native_enum=False),
        nullable=False,
        default=RSVPStatus.PENDING,
    )

    invitation_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rsvp_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Check-In ──────────────────────────────────────────────────────────────

    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the guest was physically checked in at the venue",
    )

    # ── Additional Info ───────────────────────────────────────────────────────

    dietary_preference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Dietary requirements or restrictions for catering purposes",
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_plus_one: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if this guest was added as a companion (+1) by another guest",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        back_populates="guests",
        lazy="noload",
    )

    user: Mapped[User | None] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<CelebrationGuest id={self.id} name={self.name!r} "
            f"rsvp={self.rsvp_status}>"
        )
