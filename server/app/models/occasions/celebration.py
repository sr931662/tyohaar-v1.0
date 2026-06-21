"""
Celebration — root aggregate for a customer's planned event.

Every booking, invitation, package selection, budget, guest list,
and checklist item belongs to a Celebration. This is the most important
customer-facing model in the system.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CelebrationStatus, Currency
from app.models.mixins import (
    MetadataMixin,
    NotesMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.users.address import UserAddress
    from app.models.occasions.occasion import Occasion
    from app.models.occasions.occasion_theme import OccasionTheme
    from app.models.occasions.occasion_mood import OccasionMood
    from app.models.occasions.celebration_guest import CelebrationGuest
    from app.models.occasions.celebration_timeline import CelebrationTimeline
    from app.models.occasions.celebration_note import CelebrationNote
    from app.models.occasions.celebration_budget import CelebrationBudget
    from app.models.occasions.celebration_checklist import CelebrationChecklist


class Celebration(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, MetadataMixin, Base):
    """
    A customer's planned celebration event — the central aggregate.

    One Celebration ties together:
    - A specific occasion type (Birthday, Anniversary, Diwali Puja, etc.)
    - A selected theme and mood
    - Venue and date/time details
    - Guest list with RSVP tracking
    - Package bookings (in the Bookings domain)
    - Budget allocation and tracking
    - Planning checklist and timeline milestones
    - Digital invitations

    `completion_percentage` (0–100) is computed and cached by the service
    layer based on: occasion set, package selected, guests added, invitations sent.

    Customers interact with Celebrations, never with vendors directly.
    Vendor assignments are internal, stored in `package_item_vendors`.
    """

    __tablename__ = "celebrations"

    __table_args__ = (
        Index("ix_celebrations_customer_id", "customer_id"),
        Index("ix_celebrations_occasion_id", "occasion_id"),
        Index("ix_celebrations_celebration_date", "celebration_date"),
        Index("ix_celebrations_status", "status"),
        Index("ix_celebrations_customer_status", "customer_id", "status"),
        CheckConstraint(
            "completion_percentage BETWEEN 0 AND 100",
            name="ck_celebrations_completion_pct",
        ),
        CheckConstraint(
            "guest_count >= 0",
            name="ck_celebrations_guest_count_non_negative",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer planning this celebration",
    )

    # ── Occasion Selection ────────────────────────────────────────────────────

    occasion_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The occasion type being celebrated",
    )

    theme_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasion_themes.id", ondelete="SET NULL"),
        nullable=True,
        comment="Customer's chosen visual theme (selected during planning)",
    )

    mood_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasion_moods.id", ondelete="SET NULL"),
        nullable=True,
        comment="Customer's desired celebration mood/atmosphere",
    )

    # ── Event Details ─────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Customer-provided name e.g. 'Mom\\'s 60th Birthday', 'Our 10th Anniversary'",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    celebration_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Calendar date of the celebration event",
    )

    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)

    end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)

    # ── Guests ────────────────────────────────────────────────────────────────

    guest_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Expected guest count. Updated by service layer as guests are added.",
    )

    # ── Venue ─────────────────────────────────────────────────────────────────

    venue_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Name of the venue or location (e.g. 'Home', 'Banquet Hall XYZ')",
    )

    venue_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text full address. Used when venue is not a saved UserAddress.",
    )

    venue_address_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_addresses.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to a saved UserAddress. Takes precedence over free-text venue_address.",
    )

    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)

    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)

    # ── Progress & Status ─────────────────────────────────────────────────────

    status: Mapped[CelebrationStatus] = mapped_column(
        SAEnum(CelebrationStatus, name="celebration_status", native_enum=False),
        nullable=False,
        default=CelebrationStatus.DRAFT,
        index=True,
    )

    completion_percentage: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="0–100 progress score cached from service layer. Drives home screen progress rings.",
    )

    # ── Budget ────────────────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    estimated_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Customer's self-reported budget estimate at the start of planning",
    )

    final_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Actual total after all bookings and payments are confirmed",
    )

    # ── Special Instructions ──────────────────────────────────────────────────

    special_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Customer's special requests for the celebration",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    customer: Mapped[User] = relationship("User", lazy="noload")

    occasion: Mapped[Occasion] = relationship(
        "Occasion",
        back_populates="celebrations",
        lazy="noload",
    )

    theme: Mapped[OccasionTheme | None] = relationship("OccasionTheme", lazy="noload")

    mood: Mapped[OccasionMood | None] = relationship("OccasionMood", lazy="noload")

    venue_address_obj: Mapped[UserAddress | None] = relationship(
        "UserAddress",
        lazy="noload",
    )

    guests: Mapped[list[CelebrationGuest]] = relationship(
        "CelebrationGuest",
        back_populates="celebration",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    timeline: Mapped[list[CelebrationTimeline]] = relationship(
        "CelebrationTimeline",
        back_populates="celebration",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    notes: Mapped[list[CelebrationNote]] = relationship(
        "CelebrationNote",
        back_populates="celebration",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    budget: Mapped[CelebrationBudget | None] = relationship(
        "CelebrationBudget",
        back_populates="celebration",
        uselist=False,
        lazy="noload",
        cascade="all, delete-orphan",
    )

    checklist: Mapped[list[CelebrationChecklist]] = relationship(
        "CelebrationChecklist",
        back_populates="celebration",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    @property
    def is_upcoming(self) -> bool:
        from datetime import date as _date
        return self.celebration_date >= _date.today()

    def __repr__(self) -> str:
        return (
            f"<Celebration id={self.id} title={self.title!r} "
            f"date={self.celebration_date} status={self.status}>"
        )
