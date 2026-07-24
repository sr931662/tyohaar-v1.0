"""
PackageItemReview — customer reviews of an individual package item.

Mirrors PackageReview, scoped to a single PackageItem instead of the whole
package. See package_review.py for the equivalent package-level model.
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
from app.models.enums import ReviewModerationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_item import PackageItem
    from app.models.users.user import User


class PackageItemReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A customer's review of a single package item.

    Architecture:
    - One review per (package_item_id, customer_id) — mirrors the uniqueness
      actually enforced by PackageReview's service-layer validator.
    - `booking_id` links to the booking for 'Verified Purchase' badges only;
      it is nullable and NOT unique (a customer may review an item without
      it being tied to exactly one booking lookup).
    - Only APPROVED reviews are used for item rating aggregation.
    """

    __tablename__ = "package_item_reviews"

    __table_args__ = (
        UniqueConstraint(
            "package_item_id", "customer_id", name="uq_package_item_reviews_item_customer"
        ),
        Index("ix_package_item_reviews_package_item_id", "package_item_id"),
        Index("ix_package_item_reviews_customer_id", "customer_id"),
        Index("ix_package_item_reviews_moderation", "moderation_status", "is_published"),
        Index("ix_package_item_reviews_rating", "package_item_id", "rating"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_package_item_reviews_rating_range"),
        CheckConstraint("helpful_count >= 0", name="ck_package_item_reviews_helpful_count"),
    )

    # ── Context ───────────────────────────────────────────────────────────────

    package_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="RESTRICT"),
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
        comment="FK to the booking whose item usage this reviews. Used only for "
                "the 'Verified Purchase' badge — uniqueness is enforced on "
                "(package_item_id, customer_id), not on this column.",
    )

    # ── Review Content ────────────────────────────────────────────────────────

    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Item experience rating 1 (worst) to 5 (best)",
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

    moderation_status: Mapped[ReviewModerationStatus] = mapped_column(
        SAEnum(
            ReviewModerationStatus,
            name="package_item_review_moderation_status",
            native_enum=False,
        ),
        nullable=False,
        default=ReviewModerationStatus.PENDING,
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
        comment="True only for APPROVED reviews. Controls inclusion in item rating stats.",
    )

    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of users who marked this review as helpful",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package_item: Mapped[PackageItem] = relationship(
        "PackageItem",
        back_populates="reviews",
        lazy="noload",
    )

    customer: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<PackageItemReview id={self.id} package_item_id={self.package_item_id} "
            f"rating={self.rating} status={self.moderation_status}>"
        )
