"""
CelebrationGuest — guest record for a celebration with RSVP and check-in tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import GuestEntryStatus, GuestPassStatus, RSVPStatus
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
        Index("ix_celebration_guests_entry", "celebration_id", "entry_status"),
        Index("ix_celebration_guests_pass", "celebration_id", "pass_status"),
        UniqueConstraint(
            "celebration_id",
            "client_request_id",
            name="uq_celebration_guests_client_request",
        ),
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

    # ── Invitation credentials ────────────────────────────────────────────────
    # Two independent secrets per guest (see services/invitations/credentials):
    #  * the *link token* — 32 random bytes in the guest's personal invite URL;
    #    whoever holds it can view the invite, RSVP and display the pass.
    #  * the *entry code* — 8 characters, shown on the pass and encoded in its
    #    QR. Useless on its own: only an authorised gate operator can verify it.
    # Neither is stored in the clear. *_hash is a keyed HMAC used for lookup;
    # *_enc is a reversible encryption so the host can re-share the same link.

    link_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True,
        comment="HMAC-SHA256 of the guest's invite-link token (lookup key).",
    )
    link_token_enc: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Fernet-encrypted invite-link token, decryptable for the host only.",
    )
    entry_code_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True,
        comment="HMAC-SHA256 of the normalised gate entry code (lookup key).",
    )
    entry_code_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    credentials_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    client_request_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Idempotency key from the creating client — a retried create returns the same guest.",
    )

    # ── Access rules ──────────────────────────────────────────────────────────

    pass_status: Mapped[GuestPassStatus] = mapped_column(
        SAEnum(GuestPassStatus, name="guest_pass_status", native_enum=False, length=20),
        nullable=False, default=GuestPassStatus.ACTIVE, server_default="ACTIVE",
    )
    plus_ones_allowed: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0",
        comment="Accompanying guests admitted on this pass in addition to the invitee.",
    )
    arrival_window_start: Mapped[time | None] = mapped_column(
        Time(timezone=False), nullable=True,
        comment="Expected arrival (time of day on the event date) — informational for the gate.",
    )
    arrival_window_end: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Guest's own response (kept apart from the host's private `notes`) ─────

    rsvp_party_size: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True,
        comment="How many people (invitee included) the guest said are coming.",
    )
    guest_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Free-text note the guest left with their RSVP."
    )

    # ── Gate entry ────────────────────────────────────────────────────────────

    entry_status: Mapped[GuestEntryStatus] = mapped_column(
        SAEnum(GuestEntryStatus, name="guest_entry_status", native_enum=False, length=20),
        nullable=False, default=GuestEntryStatus.NOT_ARRIVED, server_default="NOT_ARRIVED",
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_in_party_size: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    entry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # ── Sharing (only what the host's device confirmed) ───────────────────────

    last_shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_shared_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    share_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    invitation_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Set the first time the guest opens the public RSVP link. Used to "
            "distinguish 'never opened' (pending) from 'opened but didn't "
            "respond' (displayed as ignored) — see CelebrationGuestResponse.display_status."
        ),
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
