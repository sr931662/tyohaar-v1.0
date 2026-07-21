"""
Package — a curated bundle of celebration services sold to customers.

Packages are what customers browse and book. Vendor details are never exposed.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PackageStatus
from app.models.mixins import NotesMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_category import PackageCategory
    from app.models.packages.package_item import PackageItem
    from app.models.packages.package_addon import PackageAddon
    from app.models.packages.package_customization import PackageCustomization
    from app.models.packages.package_gallery import PackageGallery
    from app.models.packages.package_pricing import PackagePricing
    from app.models.packages.package_discount import PackageDiscount
    from app.models.packages.package_availability import PackageAvailability
    from app.models.packages.package_review import PackageReview
    from app.models.packages.package_faq import PackageFAQ
    from app.models.occasions.occasion import Occasion
    from app.models.occasions.occasion_theme import OccasionTheme


# ── Occasion ↔ Package M:N Association ────────────────────────────────────────
# A package can be available for multiple occasions (Festival Decoration Package
# applies to both Diwali and Navratri). Defined here; referenced in occasion.py.

package_occasions = Table(
    "package_occasions",
    Base.metadata,
    Column(
        "package_id",
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "occasion_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ── Theme ↔ Package M:N Association ───────────────────────────────────────────
# Not every celebration theme suits every package, so a vendor explicitly picks
# which of the platform's themes are offered as a customization option on a
# given (is_customizable=True) package, rather than every theme applying
# everywhere by default.

package_themes = Table(
    "package_themes",
    Base.metadata,
    Column(
        "package_id",
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "theme_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasion_themes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ── Model ─────────────────────────────────────────────────────────────────────

class Package(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, Base):
    """
    A curated bundle of celebration services.

    Customers see the package as a whole — photography + decoration + cake
    presented as one "Birthday Starter Package". The underlying vendor
    assignments are tracked in PackageItemVendor (internal, never exposed).

    `slug` is unique and used in deep-links and SEO URLs.
    `is_bestseller` and `is_featured` are set by admins.
    `popularity_score` is updated by a background job based on booking volume.
    `internal_notes` (via NotesMixin) are never exposed to customers.
    """

    __tablename__ = "packages"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_packages_slug"),
        Index("ix_packages_category_id", "category_id"),
        Index("ix_packages_status", "status"),
        Index("ix_packages_active_featured", "is_active", "is_featured"),
        Index("ix_packages_popularity", "popularity_score"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Taxonomy ──────────────────────────────────────────────────────────────

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(300), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        unique=True,
        comment="URL-safe deep-link identifier e.g. 'birthday-starter-pack'",
    )

    tagline: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Short marketing copy shown under the package name in cards",
    )

    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Capacity ──────────────────────────────────────────────────────────────

    min_guest_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum guests this package is designed for",
    )

    max_guest_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum guests this package supports",
    )

    duration_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated total setup + execution duration in hours",
    )

    # ── Pricing (denormalised for quick display) ──────────────────────────────

    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")

    # ── Customisation & Analytics ─────────────────────────────────────────────

    is_customizable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    booking_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Status & Visibility ───────────────────────────────────────────────────

    status: Mapped[PackageStatus] = mapped_column(
        SAEnum(PackageStatus, name="package_status", native_enum=False),
        nullable=False,
        default=PackageStatus.DRAFT,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Promoted on home screen and top of search results",
    )

    is_bestseller: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Shown with a 'Bestseller' badge based on booking volume",
    )

    is_recommended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Shown in 'Recommended for you' carousels",
    )

    # ── Location ──────────────────────────────────────────────────────────────

    city_slug: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
        comment="City slug where this package is offered (e.g. 'noida', 'mumbai'). "
                "Denormalized from the vendor's primary operating city for fast filtering.",
    )

    # ── Discovery ─────────────────────────────────────────────────────────────

    popularity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Denormalized score for trending/popular sorts. Updated by background job.",
    )

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ─────────────────────────────────────────────────────────

    category: Mapped[PackageCategory | None] = relationship(
        "PackageCategory",
        back_populates="packages",
        lazy="noload",
    )

    occasions: Mapped[list[Occasion]] = relationship(
        "Occasion",
        secondary="package_occasions",
        back_populates="packages",
        lazy="noload",
    )

    themes: Mapped[list[OccasionTheme]] = relationship(
        "OccasionTheme",
        secondary="package_themes",
        back_populates="packages",
        lazy="noload",
    )

    items: Mapped[list[PackageItem]] = relationship(
        "PackageItem",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    addons: Mapped[list[PackageAddon]] = relationship(
        "PackageAddon",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    customizations: Mapped[list[PackageCustomization]] = relationship(
        "PackageCustomization",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    gallery: Mapped[list[PackageGallery]] = relationship(
        "PackageGallery",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    pricing: Mapped[list[PackagePricing]] = relationship(
        "PackagePricing",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    discounts: Mapped[list[PackageDiscount]] = relationship(
        "PackageDiscount",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    availability: Mapped[list[PackageAvailability]] = relationship(
        "PackageAvailability",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    reviews: Mapped[list[PackageReview]] = relationship(
        "PackageReview",
        back_populates="package",
        lazy="noload",
    )

    faqs: Mapped[list[PackageFAQ]] = relationship(
        "PackageFAQ",
        back_populates="package",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Package id={self.id} name={self.name!r} slug={self.slug!r}>"
