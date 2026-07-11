"""
Response schemas for the packages domain.

These are the shapes returned by API endpoints. All schemas use
ConfigDict(from_attributes=True) so they can be populated directly
from SQLAlchemy ORM instances.

SECURITY: internal_notes, extra_metadata, and deleted_at are
intentionally excluded from every public response schema.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import Currency, PackagePricingType, PackageStatus, VendorType
from app.schemas.packages.common import PriceTierSchema


__all__ = [
    "PackageCategoryResponse",
    "PackageResponse",
    "PackageItemResponse",
    "PackageItemImageResponse",
    "PackageGalleryResponse",
    "PackagePricingResponse",
    "PackageDiscountResponse",
    "PackageReviewResponse",
    "PackageFAQResponse",
    "PackageAvailabilityResponse",
    "PackageVendorInfo",
    "PackageDetailResponse",
]


class PackageVendorInfo(BaseSchema):
    """Admin-facing summary of the vendor that owns a package."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    slug: str = Field(description='Human-readable code, e.g. "ctrr-noida-04234"')
    business_name: str
    owner_full_name: str | None = None
    vendor_type: VendorType


class PackageCategoryResponse(BaseSchema):
    """Public response shape for a PackageCategory."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    icon_url: str | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PackageResponse(BaseSchema):
    """
    Public response shape for a Package listing.

    Omitted fields (never exposed): internal_notes, extra_metadata, deleted_at.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    slug: str
    category_id: uuid.UUID | None = None
    description: str | None = None
    short_description: str | None = None
    cover_image_url: str | None = None
    status: PackageStatus
    is_featured: bool = False
    is_customizable: bool = False
    # Model columns are min_guest_count / max_guest_count; expose as min_guests / max_guests
    min_guests: int | None = Field(default=None, alias="min_guest_count")
    max_guests: int | None = Field(default=None, alias="max_guest_count")
    duration_hours: Decimal | None = None
    base_price: MoneyAmount | None = None
    currency: Currency = Currency.INR
    display_order: int = 0
    average_rating: Decimal | None = None
    review_count: int = 0
    booking_count: int = 0
    vendor_id: uuid.UUID | None = None
    city_slug: str | None = None
    inclusions_count: int = 0
    occasion_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PackageItemImageResponse(BaseSchema):
    """Public response shape for a PackageItemImage."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    item_id: uuid.UUID
    image_url: str
    sort_order: int = 0
    created_at: datetime


class PackageItemResponse(BaseSchema):
    """Public response shape for a PackageItem."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    name: str
    description: str | None
    quantity: int
    max_quantity: int | None = None
    unit: str | None
    base_price: MoneyAmount
    is_mandatory: bool
    is_customizable: bool = False
    icon_url: str | None = None
    display_order: int
    images: list[PackageItemImageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PackageGalleryResponse(BaseSchema):
    """Public response shape for a PackageGallery image."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    file_url: str
    caption: str | None = None
    sort_order: int = 0
    created_at: datetime


class PackagePricingResponse(BaseSchema):
    """Public response shape for a PackagePricing record."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    pricing_type: PackagePricingType
    base_price: MoneyAmount
    min_price: MoneyAmount | None
    max_price: MoneyAmount | None
    price_per_person: MoneyAmount | None
    tier_details: list[PriceTierSchema] | None
    currency: Currency
    created_at: datetime
    updated_at: datetime


class PackageDiscountResponse(BaseSchema):
    """Public response shape for a PackageDiscount."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID | None
    discount_type: str
    discount_value: Decimal
    title: str = Field(validation_alias="name")
    description: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PackageReviewResponse(BaseSchema):
    """
    Public response shape for a PackageReview.

    Soft-deleted reviews (deleted_at set) are filtered at query level;
    deleted_at is never included here.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    booking_id: uuid.UUID
    reviewer_id: uuid.UUID
    rating: int
    title: str | None
    body: str | None
    is_verified: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime


class PackageFAQResponse(BaseSchema):
    """Public response shape for a PackageFAQ."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    question: str
    answer: str
    display_order: int
    created_at: datetime
    updated_at: datetime


class PackageAvailabilityResponse(BaseSchema):
    """Public response shape for a PackageAvailability slot."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    package_id: uuid.UUID
    available_date: date
    slots_available: int
    slots_booked: int
    is_available: bool
    created_at: datetime
    updated_at: datetime


class PackageDetailResponse(PackageResponse):
    """
    Extended package response with all nested sub-resources pre-loaded.

    Used on the package detail page where all related data is fetched in one
    eager-load query. Items are ordered by display_order; discounts are
    ordered by valid_from DESC.
    """

    pricing: PackagePricingResponse | None = Field(
        default=None, description="Pricing configuration (None if not yet configured)"
    )
    items: list[PackageItemResponse] = Field(
        default_factory=list, description="Package items ordered by display_order"
    )
    gallery: list[PackageGalleryResponse] = Field(
        default_factory=list,
        description="Additional images beyond the cover — ordered by sort_order. "
                    "The cover image (cover_image_url) is always shown first on "
                    "the client and is not duplicated in this list.",
    )
    discounts: list[PackageDiscountResponse] = Field(
        default_factory=list, description="Active and upcoming discounts"
    )
    faqs: list[PackageFAQResponse] = Field(
        default_factory=list, description="FAQs ordered by display_order"
    )
    vendor: PackageVendorInfo | None = Field(
        default=None, description="Owning vendor's identity summary"
    )
