"""
PackageReview — customer reviews of their package experience.

Reviews are for the overall Tyohaar package experience, NOT for the vendor.
Vendor reviews (internal) are in vendors/vendor_review.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ReviewModerationStatus as PackageReviewModerationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package
    from app.models.users.user import User


class PackageReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A customer's review of their package experience.

    Architecture:
    - Reviews describe the customer's PACKAGE experience, not the vendor.
    - `booking_id` links to the booking for 'Verified Purchase' badges.
    - Only APPROVED reviews are used for package rating aggregation.
    - `is_verified_booking` is set to True when booking_id is confirmed complete.

    One review per booking (UNIQUE on booking_id) prevents duplicate reviews.
    """

    __tablename__ = "package_reviews"

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_package_reviews_booking_id"),
        Index("ix_package_reviews_package_id", "package_id"),
        Index("ix_package_reviews_customer_id", "customer_id"),
        Index("ix_package_reviews_moderation", "moderation_status", "is_published"),
        Index("ix_package_reviews_rating", "package_id", "rating"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_package_reviews_rating_range"),
        CheckConstraint("helpful_count >= 0", name="ck_package_reviews_helpful_count"),
    )

    # ── Context ───────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        comment="FK to booking. One review per booking enforced via UNIQUE constraint.",
    )

    # ── Review Content ────────────────────────────────────────────────────────

    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Overall package experience rating 1 (worst) to 5 (best)",
    )

    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    media_urls: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="CDN URLs for customer-uploaded review photos",
    )

    # ── Verification ──────────────────────────────────────────────────────────

    is_verified_booking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if booking_id is confirmed complete. Displays 'Verified Purchase' badge.",
    )

    # ── Moderation ────────────────────────────────────────────────────────────

    moderation_status: Mapped[PackageReviewModerationStatus] = mapped_column(
        SAEnum(
            PackageReviewModerationStatus,
            name="package_review_moderation_status",
            native_enum=False,
        ),
        nullable=False,
        default=PackageReviewModerationStatus.PENDING,
        index=True,
    )

    moderated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Tyohaar staff member who approved or rejected this review",
    )

    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    moderation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal moderation notes. Not visible to customer.",
    )

    # ── Publishing ────────────────────────────────────────────────────────────

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True only for APPROVED reviews. Controls inclusion in package rating stats.",
    )

    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of users who marked this review as helpful",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="reviews",
        lazy="noload",
    )

    customer: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<PackageReview id={self.id} package_id={self.package_id} "
            f"rating={self.rating} status={self.moderation_status}>"
        )
