"""
Functions, households and per-function responses.

These extend the existing celebration → guest model rather than sitting beside
it: a function belongs to a Celebration, a household groups CelebrationGuests,
and a response ties one guest to one function.

``GuestFunctionResponse`` is deliberately both the invitation to a function and
the answer to it. A row existing means "invited to this function"; its status
starts PENDING. That makes answering something you weren't invited to
unrepresentable.

An event with no functions still gets one row per responding guest, with
``function_id`` NULL, so food preferences have the same home in both cases.
``CelebrationGuest.rsvp_status`` stays the rolled-up answer the gate, the guest
list and every older client already read (see rules.rollup_rsvp).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import GuestGroupResponseMode, RSVPStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CelebrationFunction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One part of an event: Haldi, Mehendi, Wedding, Reception…"""

    __tablename__ = "celebration_functions"
    __table_args__ = (Index("ix_celebration_functions_event", "celebration_id", "display_order"),)

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    function_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    venue_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dress_code: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")


class CelebrationGuestGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A household invited together. It introduces no token of its own: the
    primary guest's existing personal link opens the whole household, so link
    rotation, revocation and hashing all behave exactly as they do for one guest.
    """

    __tablename__ = "celebration_guest_groups"
    __table_args__ = (
        Index("ix_celebration_guest_groups_event", "celebration_id"),
        CheckConstraint(
            "invitation_capacity IS NULL OR invitation_capacity >= 1",
            name="ck_celebration_guest_groups_capacity",
        ),
    )

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invitation_capacity: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True,
        comment="Most people this household may bring in total. NULL = per-member allowances only.",
    )
    response_mode: Mapped[GuestGroupResponseMode] = mapped_column(
        SAEnum(GuestGroupResponseMode, name="guest_group_response_mode", native_enum=False, length=20),
        nullable=False,
        default=GuestGroupResponseMode.GROUP,
        server_default="GROUP",
    )
    primary_guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebration_guests.id", ondelete="SET NULL", use_alter=True, name="fk_guest_groups_primary_guest"),
        nullable=True,
        comment="Whose link opens the whole household.",
    )


class GuestFunctionResponse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One guest's invitation to, and answer for, one function."""

    __tablename__ = "guest_function_responses"
    __table_args__ = (
        # Two partial indexes rather than one: NULLs are distinct in a plain
        # unique index, which would allow duplicate answers on no-function events.
        Index(
            "uq_guest_function_response",
            "celebration_guest_id",
            "function_id",
            unique=True,
            postgresql_where=text("function_id IS NOT NULL"),
        ),
        Index(
            "uq_guest_event_response",
            "celebration_guest_id",
            unique=True,
            postgresql_where=text("function_id IS NULL"),
        ),
        Index("ix_guest_function_responses_event", "celebration_id", "function_id", "status"),
        CheckConstraint("attendee_count IS NULL OR attendee_count >= 0", name="ck_guest_function_responses_attendees"),
    )

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("celebrations.id", ondelete="CASCADE"), nullable=False
    )
    function_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("celebration_functions.id", ondelete="CASCADE"), nullable=True
    )
    celebration_guest_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("celebration_guests.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RSVPStatus] = mapped_column(
        SAEnum(RSVPStatus, name="rsvp_status", native_enum=False),
        nullable=False,
        default=RSVPStatus.PENDING,
        server_default="PENDING",
    )
    attendee_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Food. Lives here because a meal preference only means something for a
    # specific function; a separate table would be 1:1 with this one.
    dietary_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="vegetarian | non_vegetarian | jain | vegan | other",
    )
    meal_selection: Mapped[str | None] = mapped_column(String(120), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    answers: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Answers to organiser-defined questions, keyed by question id.",
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
