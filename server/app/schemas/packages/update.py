"""
Update (PATCH body) schemas for the packages domain.

All fields are Optional so callers can send partial updates. The service
layer merges only the supplied fields onto the existing ORM instance.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import Currency, PackagePricingType, PackageStatus
from app.schemas.packages.common import PriceTierSchema


__all__ = [
    "PackageUpdate",
    "PackageCategoryUpdate",
    "PackageItemUpdate",
    "PackagePricingUpdate",
    "PackageDiscountUpdate",
    "PackageReviewUpdate",
    "PackageFAQUpdate",
    "PackageAvailabilityUpdate",
]


class PackageCategoryUpdate(BaseSchema):
    """Partial update payload for a PackageCategory."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = None
    icon_url: str | None = Field(default=None, max_length=2048)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)

    @field_validator("slug", mode="before")
    @classmethod
    def normalise_slug(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v


class PackageUpdate(BaseSchema):
    """Partial update payload for a Package listing."""

    name: str | None = Field(default=None, min_length=1, max_length=300)
    slug: str | None = Field(
        default=None,
        max_length=200,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    category_id: uuid.UUID | None = None
    description: str | None = None
    short_description: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    status: PackageStatus | None = None
    is_featured: bool | None = None
    is_customizable: bool | None = None
    min_guests: int | None = Field(default=None, ge=1, le=32767)
    max_guests: int | None = Field(default=None, ge=1, le=32767)
    duration_hours: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=2)
    base_price: MoneyAmount | None = None
    currency: Currency | None = None
    display_order: int | None = Field(default=None, ge=0)
    city_slug: str | None = Field(default=None, max_length=200)

    @field_validator("slug", mode="before")
    @classmethod
    def normalise_slug(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def validate_guest_range(self) -> "PackageUpdate":
        if (
            self.min_guests is not None
            and self.max_guests is not None
            and self.min_guests > self.max_guests
        ):
            raise ValueError("min_guests must be ≤ max_guests")
        return self


class PackageItemUpdate(BaseSchema):
    """Partial update payload for a PackageItem."""

    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit: str | None = Field(default=None, max_length=50)
    base_price: MoneyAmount | None = None
    is_mandatory: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class PackagePricingUpdate(BaseSchema):
    """Partial update payload for a PackagePricing record."""

    pricing_type: PackagePricingType | None = None
    base_price: MoneyAmount | None = None
    min_price: MoneyAmount | None = None
    max_price: MoneyAmount | None = None
    price_per_person: MoneyAmount | None = None
    tier_details: list[PriceTierSchema] | None = None
    currency: Currency | None = None

    @model_validator(mode="after")
    def validate_price_range(self) -> "PackagePricingUpdate":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be ≤ max_price")
        return self


class PackageDiscountUpdate(BaseSchema):
    """Partial update payload for a PackageDiscount."""

    discount_type: str | None = Field(default=None, min_length=1, max_length=50)
    discount_value: Decimal | None = Field(default=None, ge=Decimal("0"), decimal_places=2)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None

    @field_validator("discount_type", mode="before")
    @classmethod
    def normalise_discount_type(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "PackageDiscountUpdate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be before valid_until")
        return self


class PackageReviewUpdate(BaseSchema):
    """
    Partial update payload for a PackageReview.

    Customers may update rating/title/body for a grace period after submission.
    Admins additionally control is_published for moderation.
    """

    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    body: str | None = None
    is_published: bool | None = Field(
        default=None,
        description="Admin-only: approve or hide this review",
    )


class PackageFAQUpdate(BaseSchema):
    """Partial update payload for a PackageFAQ."""

    question: str | None = Field(default=None, min_length=1, max_length=500)
    answer: str | None = Field(default=None, min_length=1)
    display_order: int | None = Field(default=None, ge=0)


class PackageAvailabilityUpdate(BaseSchema):
    """Partial update payload for a PackageAvailability slot."""

    available_date: date | None = None
    slots_available: int | None = Field(default=None, ge=0, le=32767)
    slots_booked: int | None = Field(
        default=None,
        ge=0,
        le=32767,
        description="Service-layer managed; do not send from client",
    )
    is_available: bool | None = None
