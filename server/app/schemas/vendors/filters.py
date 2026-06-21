"""
Query-parameter filter schemas for the vendors domain.

These schemas are used as FastAPI dependency injections via
`Depends(VendorFilters)` or `Query(...)` patterns.
All fields are Optional so callers may omit any subset.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.models.enums import (
    VendorType,
    VendorStatus,
    VendorVerificationStatus,
    ServiceStatus,
    PackagePricingType,
)

__all__ = [
    "VendorFilters",
    "VendorServiceFilters",
    "VendorReviewFilters",
]


class VendorFilters(BaseSchema):
    """
    Filtering parameters for the vendor listing endpoint.

    All fields are optional; omit any field to skip that filter.
    """

    model_config = ConfigDict(populate_by_name=True)

    vendor_type: VendorType | None = Field(
        default=None,
        description="Filter by primary service category",
    )
    status: VendorStatus | None = Field(
        default=None,
        description="Filter by operational status",
    )
    verification_status: VendorVerificationStatus | None = Field(
        default=None,
        description="Filter by KYC verification state",
    )
    is_active: bool | None = Field(
        default=None,
        description="Return only active (True) or inactive (False) vendors",
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        description="Filter vendors that operate in this city",
    )
    state: str | None = Field(
        default=None,
        max_length=100,
        description="Filter vendors that operate in this state",
    )
    min_rating: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("5"),
        decimal_places=2,
        description="Minimum average rating (inclusive)",
    )
    service_radius_km: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        description="Return only vendors whose service_radius_km >= this value",
    )
    search: str | None = Field(
        default=None,
        max_length=200,
        description="Full-text search on business_name and tagline",
    )


class VendorServiceFilters(BaseSchema):
    """Filtering parameters for the vendor-service listing endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    vendor_id: uuid.UUID | None = Field(
        default=None,
        description="Return only services belonging to this vendor",
    )
    category_id: uuid.UUID | None = Field(
        default=None,
        description="Return only services in this category",
    )
    status: ServiceStatus | None = Field(
        default=None,
        description="Filter by service availability status",
    )
    is_active: bool | None = Field(
        default=None,
        description="Return only active / inactive services",
    )
    min_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Minimum base_price (inclusive)",
    )
    max_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Maximum base_price (inclusive)",
    )
    pricing_type: PackagePricingType | None = Field(
        default=None,
        description="Filter by pricing model",
    )


class VendorReviewFilters(BaseSchema):
    """Filtering parameters for the vendor-review listing endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    vendor_id: uuid.UUID | None = Field(
        default=None,
        description="Return reviews for this vendor only",
    )
    reviewer_id: uuid.UUID | None = Field(
        default=None,
        description="Return reviews written by this user only",
    )
    rating: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Filter by exact star rating",
    )
    is_published: bool | None = Field(
        default=None,
        description="Return only published / unpublished reviews",
    )
    is_verified: bool | None = Field(
        default=None,
        description="Return only booking-verified reviews",
    )
    from_date: date | None = Field(
        default=None,
        description="Return reviews created on or after this date (YYYY-MM-DD)",
    )
    to_date: date | None = Field(
        default=None,
        description="Return reviews created on or before this date (YYYY-MM-DD)",
    )
