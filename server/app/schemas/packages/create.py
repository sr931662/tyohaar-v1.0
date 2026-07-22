"""
Create (POST body) schemas for the packages domain.

All fields here are what a client or admin must supply when creating a
new package-related resource. IDs and timestamps are never accepted on
create; they are assigned by the server.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import Currency, PackagePricingType, PackageStatus
from app.schemas.packages.common import PriceTierSchema


__all__ = [
    "PackageCreate",
    "PackageCategoryCreate",
    "PackageItemCreate",
    "PackageGalleryCreate",
    "PackageItemImageCreate",
    "PackagePricingCreate",
    "PackageDiscountCreate",
    "PackageReviewCreate",
    "PackageFAQCreate",
    "PackageAvailabilityCreate",
]


class PackageCategoryCreate(BaseSchema):
    """Payload required to create a new package category."""

    name: str = Field(min_length=1, max_length=200, description="Category display name")
    slug: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe lowercase slug (auto-generated from name if omitted)",
    )
    description: str | None = Field(default=None, description="Category description")
    icon_url: str | None = Field(default=None, max_length=2048, description="Icon asset URL")
    is_active: bool = Field(default=True, description="Whether this category is visible")
    sort_order: int = Field(default=0, ge=0, description="Sort order (lower = earlier)")


class PackageCreate(BaseSchema):
    """Payload required to create a new package listing."""

    name: str = Field(min_length=1, max_length=300, description="Package display name")
    slug: str | None = Field(
        default=None,
        max_length=200,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe slug; auto-generated from name if not provided",
    )
    category_id: uuid.UUID | None = Field(
        default=None, description="FK to PackageCategory"
    )
    occasion_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Occasions this package applies to (e.g. Birthday, Baby Shower).",
    )
    theme_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=1,
        description=(
            "The single celebration theme the vendor is offering on this "
            "package (at most one — customers do not choose among multiple "
            "themes). Only meaningful when is_customizable=True."
        ),
    )
    description: str | None = Field(default=None, description="Long-form description (Markdown)")
    short_description: str | None = Field(
        default=None, max_length=500, description="One-liner shown in listing cards"
    )
    cover_image_url: str | None = Field(
        default=None, max_length=2048, description="Primary cover image URL"
    )
    status: PackageStatus = Field(
        default=PackageStatus.DRAFT, description="Publication status"
    )
    is_featured: bool = Field(default=False, description="Pin to featured slots on home screen")
    is_customizable: bool = Field(
        default=False, description="Allow customers to customise items/add-ons"
    )
    min_guests: int | None = Field(default=None, ge=1, le=32767, description="Minimum party size")
    max_guests: int | None = Field(default=None, ge=1, le=32767, description="Maximum party size")
    duration_hours: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        decimal_places=2,
        description="Approximate service duration in hours",
    )
    base_price: MoneyAmount = Field(description="Starting / reference price")
    currency: Currency = Field(default=Currency.INR, description="ISO 4217 currency code")
    display_order: int = Field(default=0, ge=0, description="Sort order in category listings")
    city_slug: str | None = Field(
        default=None,
        max_length=200,
        description="City slug where this package is offered (e.g. 'noida', 'mumbai'). "
                    "Should match one of the vendor's operating_cities.",
    )

    @field_validator("slug", mode="before")
    @classmethod
    def normalise_slug(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def validate_guest_range(self) -> "PackageCreate":
        if (
            self.min_guests is not None
            and self.max_guests is not None
            and self.min_guests > self.max_guests
        ):
            raise ValueError("min_guests must be ≤ max_guests")
        return self


class PackageItemCreate(BaseSchema):
    """Payload required to add an item to an existing package."""

    package_id: uuid.UUID = Field(description="Parent package UUID")
    name: str = Field(min_length=1, max_length=300, description="Item name")
    description: str | None = Field(default=None, description="Item description")
    quantity: int = Field(default=1, ge=1, description="Default quantity included")
    unit: str | None = Field(
        default=None, max_length=50, description="Unit label, e.g. 'hours', 'pieces'"
    )
    base_price: MoneyAmount = Field(description="Item base price")
    is_mandatory: bool = Field(
        default=True, description="Whether item is always included vs. optional add-on"
    )
    is_customizable: bool = Field(
        default=False, description="True if the customer can configure options for this item"
    )
    max_quantity: int | None = Field(
        default=None,
        ge=1,
        description="Highest quantity a customer may select at booking time. "
                    "NULL means uncapped.",
    )
    icon_url: str | None = Field(default=None, max_length=500, description="Small icon/thumbnail URL")
    cover_image_url: str | None = Field(
        default=None, max_length=500,
        description="Item's cover/thumbnail image, shown on item rows and as the first gallery slide",
    )
    display_order: int = Field(default=0, ge=0, description="Sort order within the package")
    prep_time_minutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="Vendor-suggested setup/prep time (minutes) required before the event's scheduled start",
    )


class CommonPackageItemCreate(BaseSchema):
    """
    Payload to create a vendor-owned reusable item template.

    Unlike PackageItemCreate, this has no package_id — a common item is
    created once per vendor and attached to any number of that vendor's
    packages afterward via the attach/detach endpoints.
    """

    name: str = Field(min_length=1, max_length=300, description="Item name")
    description: str | None = Field(default=None, description="Item description")
    quantity: int = Field(default=1, ge=1, description="Default quantity included")
    unit: str | None = Field(
        default=None, max_length=50, description="Unit label, e.g. 'hours', 'pieces'"
    )
    base_price: MoneyAmount = Field(description="Item base price")
    is_customizable: bool = Field(
        default=False, description="True if the customer can configure options for this item"
    )
    max_quantity: int | None = Field(
        default=None,
        ge=1,
        description="Highest quantity a customer may select at booking time. "
                    "NULL means uncapped.",
    )
    icon_url: str | None = Field(default=None, max_length=500, description="Small icon/thumbnail URL")
    prep_time_minutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="Vendor-suggested setup/prep time (minutes) required before the event's scheduled start",
    )


class PackageGalleryCreate(BaseSchema):
    """Payload required to add an additional image to a package's gallery."""

    file_url: str = Field(min_length=1, max_length=500, description="CDN URL of the uploaded image")
    caption: str | None = Field(default=None, max_length=500, description="Optional caption")


class PackageItemImageCreate(BaseSchema):
    """Payload required to add a photo to a PackageItem."""

    image_url: str = Field(min_length=1, max_length=500, description="CDN URL of the uploaded image")


class PackagePricingCreate(BaseSchema):
    """Payload required to set pricing configuration for a package."""

    package_id: uuid.UUID = Field(description="Parent package UUID (unique — one pricing per package)")
    pricing_type: PackagePricingType = Field(description="Pricing strategy")
    base_price: MoneyAmount = Field(description="Base / starting price")
    min_price: MoneyAmount | None = Field(
        default=None, description="Minimum possible price (for TIERED / CUSTOM_QUOTE)"
    )
    max_price: MoneyAmount | None = Field(
        default=None, description="Maximum possible price cap"
    )
    price_per_person: MoneyAmount | None = Field(
        default=None, description="Per-person price (required for PER_PERSON type)"
    )
    tier_details: list[PriceTierSchema] | None = Field(
        default=None, description="Ordered list of price tiers (required for TIERED type)"
    )
    currency: Currency = Field(default=Currency.INR, description="Pricing currency")

    @model_validator(mode="after")
    def validate_pricing_fields(self) -> "PackagePricingCreate":
        if self.pricing_type == PackagePricingType.PER_PERSON and self.price_per_person is None:
            raise ValueError("price_per_person is required for PER_PERSON pricing type")
        if self.pricing_type == PackagePricingType.TIERED and not self.tier_details:
            raise ValueError("tier_details must be non-empty for TIERED pricing type")
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price must be ≤ max_price")
        return self


class PackageDiscountCreate(BaseSchema):
    """Payload required to attach a discount to a package."""

    package_id: uuid.UUID = Field(description="Target package UUID")
    discount_type: str = Field(
        min_length=1,
        max_length=50,
        description="Discount category, e.g. 'percentage' or 'fixed_amount'",
    )
    discount_value: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Discount magnitude (percentage points or absolute amount)",
    )
    title: str = Field(min_length=1, max_length=200, description="Short discount label")
    description: str | None = Field(default=None, description="Detailed discount description")
    valid_from: datetime | None = Field(
        default=None, description="UTC datetime when discount becomes active"
    )
    valid_until: datetime | None = Field(
        default=None, description="UTC datetime when discount expires"
    )

    @field_validator("discount_type", mode="before")
    @classmethod
    def normalise_discount_type(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_date_range(self) -> "PackageDiscountCreate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be before valid_until")
        return self


class PackageReviewCreate(BaseSchema):
    """Payload required to submit a review for a package."""

    package_id: uuid.UUID = Field(description="Reviewed package UUID")
    booking_id: uuid.UUID = Field(
        description="Booking that unlocks the right to review (1:1 guard)"
    )
    reviewer_id: uuid.UUID = Field(description="UUID of the reviewing user")
    rating: int = Field(ge=1, le=5, description="Star rating from 1 (worst) to 5 (best)")
    title: str | None = Field(default=None, max_length=200, description="Review headline")
    body: str | None = Field(default=None, description="Full review text")


class PackageFAQCreate(BaseSchema):
    """Payload required to add a FAQ entry to a package."""

    package_id: uuid.UUID = Field(description="Parent package UUID")
    question: str = Field(min_length=1, max_length=500, description="FAQ question")
    answer: str = Field(min_length=1, description="FAQ answer (Markdown supported)")
    display_order: int = Field(default=0, ge=0, description="Sort order within the FAQ list")


class PackageAvailabilityCreate(BaseSchema):
    """Payload required to create an availability slot for a package on a date."""

    package_id: uuid.UUID = Field(description="Parent package UUID")
    available_date: date = Field(description="Calendar date this slot applies to")
    slots_available: int = Field(
        ge=0, le=32767, description="Total slots offered on this date"
    )
    is_available: bool = Field(default=True, description="Override flag to block the date")
