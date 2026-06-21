"""
VendorProfile — operational and public-facing business information for a vendor.

Used internally by Tyohaar staff and the platform's matching engine.
Never exposed raw to customers.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import MetadataMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorProfile(UUIDPrimaryKeyMixin, TimestampMixin, MetadataMixin, Base):
    """
    Extended operational profile for a Vendor.

    One-to-one with Vendor. Created automatically when a vendor completes
    their onboarding wizard.

    `working_hours` JSONB structure:
        {
            "monday":    {"open": "09:00", "close": "18:00", "is_open": true},
            "tuesday":   {"open": "09:00", "close": "18:00", "is_open": true},
            ...
            "sunday":    {"is_open": false}
        }

    `holiday_calendar` JSONB structure:
        ["2026-01-26", "2026-08-15", "2026-10-02"]  (ISO-8601 dates)

    `social_links` JSONB structure:
        {
            "instagram": "https://instagram.com/handle",
            "youtube":   "https://youtube.com/@channel",
            "facebook":  "https://facebook.com/page"
        }
    """

    __tablename__ = "vendor_profiles"

    __table_args__ = (
        UniqueConstraint("vendor_id", name="uq_vendor_profiles_vendor_id"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ── Visual Identity ───────────────────────────────────────────────────────

    logo_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the vendor's business logo",
    )

    cover_image_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the vendor profile hero/banner image",
    )

    # ── Business Description ──────────────────────────────────────────────────

    tagline: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Short brand tagline (e.g., 'Making Every Moment Magical')",
    )

    about: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full business description. Used in internal CRM and vendor briefings.",
    )

    specialties: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Array of specialty strings (e.g., ['Mehendi Events', 'Theme Parties']). "
            "Used by the matching engine to surface relevant vendors."
        ),
    )

    # ── Operations ────────────────────────────────────────────────────────────

    working_hours: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Keyed by lowercase day name. See module docstring for structure.",
    )

    holiday_calendar: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="ISO-8601 dates the vendor is always closed (national/religious holidays)",
    )

    operating_cities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment="Cities where this vendor actively takes bookings",
    )

    operating_pincodes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(10)),
        nullable=True,
        comment="Specific PIN codes serviced; used for last-mile accuracy",
    )

    # ── Online Presence ───────────────────────────────────────────────────────

    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    social_links: Mapped[dict[str, str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Platform-keyed social media URLs. See module docstring for structure.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="profile")

    def __repr__(self) -> str:
        return f"<VendorProfile vendor_id={self.vendor_id} tagline={self.tagline!r}>"
