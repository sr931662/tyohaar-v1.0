"""
UserProfile — personal and demographic data, separated from authentication concerns.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, Gender, Language
from app.models.mixins import MetadataMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, MetadataMixin, Base):
    """
    Extended personal profile for a User.

    One-to-one with User; created lazily on first profile edit.
    Keeps sensitive demographic data separate from auth records,
    allowing different access control policies on each table.

    Location fields (city, state, country) represent the user's home base,
    not a delivery address. Delivery addresses live in UserAddress.
    """

    __tablename__ = "user_profiles"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        Index("ix_user_profiles_city_state", "city", "state"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ── Visual Identity ───────────────────────────────────────────────────────

    profile_photo_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the user's profile photo",
    )

    cover_image_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the profile cover/banner image",
    )

    # ── Personal ──────────────────────────────────────────────────────────────

    gender: Mapped[Gender | None] = mapped_column(
        SAEnum(Gender, name="gender", native_enum=False),
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Used for birthday reminders and age-gating where applicable",
    )

    anniversary_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Wedding or relationship anniversary. Used for occasion recommendations.",
    )

    occupation: Mapped[str | None] = mapped_column(String(200), nullable=True)

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short personal description shown on community features",
    )

    religion: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional. Used to surface culturally relevant occasions and vendors.",
    )

    # ── Preferences ───────────────────────────────────────────────────────────

    preferred_language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language", native_enum=False),
        nullable=False,
        default=Language.ENGLISH,
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Asia/Kolkata",
        comment="IANA timezone string. Defaults to IST for Indian users.",
    )

    preferred_currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    # ── Location (Home Base) ──────────────────────────────────────────────────

    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Emergency & Alternate Contact ─────────────────────────────────────────

    alternate_phone: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="Secondary contact number for event coordination",
    )

    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    emergency_contact_phone: Mapped[str | None] = mapped_column(String(15), nullable=True)

    emergency_contact_relation: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Relationship to the emergency contact (e.g., Spouse, Parent)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id}>"
