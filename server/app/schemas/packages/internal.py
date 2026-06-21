"""
Internal-only schemas for the packages domain.

These schemas are NEVER serialised to API responses. They are used
exclusively within the service and repository layers for admin
operations, background jobs, and audit trails.

WARNING: These schemas include sensitive fields (internal_notes,
extra_metadata, deleted_at) that must never reach public endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import Currency, PackageStatus
from app.schemas.packages.response import PackageResponse


__all__ = [
    "PackageInternal",
    "PackageAdminStats",
]


class PackageInternal(PackageResponse):
    """
    Full package record including admin-only fields.

    Extends the public PackageResponse with fields that must remain
    server-side only. The service layer returns this type to admin
    handlers only — never to customer-facing endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Admin-only sensitive fields
    internal_notes: str | None = Field(
        default=None,
        description="Internal admin notes — never expose to customers",
    )
    extra_metadata: dict | None = Field(
        default=None,
        description="Arbitrary JSON metadata for integrations — internal only",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp; None means record is live",
    )


class PackageAdminStats(BaseSchema):
    """
    Aggregated statistics for the packages admin dashboard.

    Computed by the analytics service layer over a rolling window.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_packages: int = Field(description="Total packages including drafts")
    active_packages: int = Field(description="Packages with status=ACTIVE")
    draft_packages: int = Field(description="Packages with status=DRAFT")
    archived_packages: int = Field(description="Packages with status=ARCHIVED")
    total_bookings: int = Field(description="Sum of booking_count across all packages")
    average_rating: Decimal | None = Field(
        default=None,
        decimal_places=2,
        description="Platform-wide average star rating across all reviewed packages",
    )
    top_package_id: uuid.UUID | None = Field(
        default=None, description="Package with the highest booking_count"
    )
    revenue_total: MoneyAmount = Field(
        description="Total revenue attributed to packages (sum of confirmed bookings)"
    )
    currency: Currency = Field(
        default=Currency.INR,
        description="Currency in which revenue_total is expressed",
    )
    computed_at: datetime = Field(
        description="UTC timestamp when these stats were last computed"
    )
