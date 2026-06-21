"""
VendorReview — customer experience reviews, internally mapped to vendors.

Customers rate their EXPERIENCE with Tyohaar.
The vendor mapping is internal and never exposed to customers.
"""

from __future__ import annotations

import enum
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.vendors.vendor import Vendor


class ReviewModerationStatus(str, enum.Enum):
    """
    Content moderation lifecycle for a customer review.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"       # Submitted; awaiting moderation
    APPROVED = "approved"     # Passed moderation; included in vendor stats
    REJECTED = "rejected"     # Violated guidelines; excluded from stats
    FLAGGED = "flagged"       # Auto-flagged or user-reported; needs human review
    HIDDEN = "hidden"         # Was approved but later hidden by admin action


class VendorReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A review submitted by a customer for a completed booking.

    Architecture:
    - Customers submit reviews for their Tyohaar experience (booking-centric).
    - Internally, each review is linked to the vendor who executed the booking.
    - `vendor_id` is NEVER sent to the customer in API responses.
    - Only APPROVED reviews are included in Vendor.average_rating calculations.

    Integrity constraints:
    - One review per booking (unique on booking_id) prevents duplicate reviews.
    - Rating is constrained to 1–5 by CHECK constraint.

    Vendor response:
    - Vendors may reply to reviews through the vendor portal.
    - Responses are subject to the same moderation pipeline.
    """

    __tablename__ = "vendor_reviews"

    __table_args__ = (
        # One review per booking
        UniqueConstraint("booking_id", name="uq_vendor_reviews_booking_id"),
        Index("ix_vendor_reviews_vendor_id", "vendor_id"),
        Index("ix_vendor_reviews_customer_id", "customer_id"),
        Index("ix_vendor_reviews_moderation_status", "moderation_status", "is_published"),
        Index("ix_vendor_reviews_rating", "vendor_id", "rating"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_vendor_reviews_rating_range"),
        CheckConstraint("helpful_count >= 0", name="ck_vendor_reviews_helpful_count"),
    )

    # ── Internal Association (never expose to customer) ───────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Internal FK to vendor. NEVER include in customer-facing API responses.",
    )

    # ── Public Context ────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        comment="The booking this review is about. One review per booking enforced.",
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer who submitted this review",
    )

    # ── Review Content ────────────────────────────────────────────────────────

    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="Overall experience rating from 1 (worst) to 5 (best)",
    )

    title: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Short review headline written by the customer",
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full review text",
    )

    media_urls: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of CDN URLs for photos attached to the review",
    )

    # ── Vendor Response ───────────────────────────────────────────────────────

    vendor_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Vendor's reply to this review. Subject to moderation before publishing.",
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Moderation ────────────────────────────────────────────────────────────

    moderation_status: Mapped[ReviewModerationStatus] = mapped_column(
        SAEnum(ReviewModerationStatus, name="review_moderation_status", native_enum=False),
        nullable=False,
        default=ReviewModerationStatus.PENDING,
        index=True,
    )

    moderated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Tyohaar staff member who approved or rejected this review",
    )

    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    moderation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal moderation notes. Not visible to customer or vendor.",
    )

    # ── Publishing ────────────────────────────────────────────────────────────

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True only for APPROVED reviews. Controls inclusion in vendor stats "
            "and visibility in internal dashboards."
        ),
    )

    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of users who marked this review as helpful",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="reviews")
    customer: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<VendorReview id={self.id} vendor_id={self.vendor_id} "
            f"rating={self.rating} status={self.moderation_status}>"
        )
