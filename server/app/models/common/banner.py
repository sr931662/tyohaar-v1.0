"""
Banner — CMS-managed promotional banners displayed in the mobile and web apps.

Banners drive user discovery and conversion across multiple surfaces:
- Home screen hero carousel (BannerType.HERO)
- Offers & Promotions tab (BannerType.PROMOTIONAL)
- Platform announcements in the notification centre (BannerType.ANNOUNCEMENT)
- Vendor spotlight cards on the vendor listing page (BannerType.VENDOR_SPOTLIGHT)
- Occasion/category feature blocks (BannerType.CATEGORY_FEATURE)

A banner is active when:
    is_active = True
    AND status = PUBLISHED
    AND (display_start_at IS NULL OR display_start_at <= now())
    AND (display_end_at IS NULL OR display_end_at >= now())
    AND deleted_at IS NULL

`target_audience` gates which user segment sees the banner.  The app queries
the appropriate segment based on the authenticated user's role and membership tier.

`target_occasion_id` and `target_vendor_id` allow deep-linking banners to
specific occasions or vendor profile pages within the app.

Impression and click metrics are denormalized for fast admin dashboard reads;
the authoritative analytics data lives in the analytics events pipeline.

`cta_deep_link` takes precedence over `cta_url` for mobile clients.  Web
clients fall back to `cta_url`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BannerTargetAudience, BannerType, ContentStatus
from app.models.mixins import AuditMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion import Occasion
    from app.models.vendors.vendor import Vendor


class Banner(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    """
    A CMS-managed promotional banner shown in app and web surfaces.

    Lifecycle:
        DRAFT → (admin edits) → SCHEDULED → (auto-publish at display_start_at)
             → PUBLISHED → (auto-expire at display_end_at) → ARCHIVED

    Admin users can manually transition any state except bypassing DRAFT→PUBLISHED
    without a scheduled date (to enforce review workflows).

    Content delivery rules (applied in order, all must pass):
        1. deleted_at IS NULL
        2. is_active = True
        3. status = 'published'
        4. display_start_at IS NULL OR display_start_at <= now()
        5. display_end_at IS NULL OR display_end_at >= now()
        6. target_audience matches the requesting user's segment

    Denormalized metrics:
    - `impressions_count` — incremented asynchronously per unique view event.
    - `click_count` — incremented on CTA tap/click.
    These are approximations; the analytics pipeline is authoritative.
    """

    __tablename__ = "banners"

    __table_args__ = (
        Index("ix_banners_banner_type", "banner_type"),
        Index("ix_banners_target_audience", "target_audience"),
        Index("ix_banners_status", "status"),
        Index("ix_banners_is_active", "is_active"),
        Index("ix_banners_display_order", "display_order"),
        Index("ix_banners_schedule", "display_start_at", "display_end_at"),
        Index("ix_banners_target_occasion_id", "target_occasion_id"),
        Index("ix_banners_target_vendor_id", "target_vendor_id"),
        CheckConstraint("display_order >= 0", name="ck_banners_display_order_non_negative"),
        CheckConstraint("impressions_count >= 0", name="ck_banners_impressions_non_negative"),
        CheckConstraint("click_count >= 0", name="ck_banners_click_count_non_negative"),
        CheckConstraint(
            "display_end_at IS NULL OR display_start_at IS NULL OR display_end_at > display_start_at",
            name="ck_banners_end_after_start",
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Primary heading displayed on the banner",
    )

    subtitle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional secondary line below the title",
    )

    # ── Classification ────────────────────────────────────────────────────────

    banner_type: Mapped[BannerType] = mapped_column(
        SAEnum(BannerType, name="banner_type", native_enum=False),
        nullable=False,
        comment="Display surface and purpose of this banner",
    )

    target_audience: Mapped[BannerTargetAudience] = mapped_column(
        SAEnum(BannerTargetAudience, name="banner_target_audience", native_enum=False),
        nullable=False,
        default=BannerTargetAudience.ALL,
        comment="User segment that should receive this banner",
    )

    # ── Media ─────────────────────────────────────────────────────────────────

    image_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="CDN URL of the banner image for desktop/web (recommended 1440×480px)",
    )

    mobile_image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment=(
            "CDN URL of a smaller banner image optimised for mobile (recommended 750×300px). "
            "Falls back to image_url when NULL."
        ),
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Image alt text for screen readers and SEO",
    )

    # ── Call To Action ────────────────────────────────────────────────────────

    cta_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Button label displayed on the banner (e.g. 'Book Now', 'View Offer')",
    )

    cta_deep_link: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "Tyohaar deep-link URI for mobile clients (e.g. 'tyohaar://occasion/birthday'). "
            "Takes precedence over cta_url on mobile."
        ),
    )

    cta_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Web URL for CTA fallback on browser clients (e.g. '/occasions/birthday')",
    )

    # ── Targeting ─────────────────────────────────────────────────────────────

    target_occasion_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Pin this banner to a specific occasion (e.g. all Birthday banners)",
    )

    target_vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        comment="Pin this banner to a specific vendor for spotlight promotions",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    display_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When to start showing this banner. NULL = show immediately once published.",
    )

    display_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When to stop showing this banner. NULL = show indefinitely.",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the banner was first published (status → PUBLISHED)",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Sort rank within the same banner_type carousel (lower = first)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False immediately hides the banner from all surfaces",
    )

    # ── CMS Status ────────────────────────────────────────────────────────────

    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", native_enum=False),
        nullable=False,
        default=ContentStatus.DRAFT,
        comment="CMS publication lifecycle state",
    )

    # ── Analytics (denormalized) ──────────────────────────────────────────────

    impressions_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Approximate unique impression count. Incremented asynchronously. "
            "Not suitable for billing; analytics pipeline is authoritative."
        ),
    )

    click_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Approximate CTA click/tap count. Incremented asynchronously.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    target_occasion: Mapped[Occasion | None] = relationship(
        "Occasion",
        lazy="noload",
    )

    target_vendor: Mapped[Vendor | None] = relationship(
        "Vendor",
        lazy="noload",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def click_through_rate(self) -> float:
        """CTR = click_count / impressions_count. Returns 0.0 when no impressions."""
        if not self.impressions_count:
            return 0.0
        return self.click_count / self.impressions_count

    def __repr__(self) -> str:
        return (
            f"<Banner id={self.id} title={self.title!r} "
            f"type={self.banner_type} status={self.status}>"
        )
