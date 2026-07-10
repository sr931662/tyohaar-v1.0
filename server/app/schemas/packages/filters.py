"""
Query-filter schemas for the packages domain.

These are used as FastAPI dependency-injected query-parameter models.
All fields are Optional; unset fields are ignored by the repository layer.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema, MoneyAmount
from app.models.enums import Currency, PackageStatus


__all__ = [
    "PackageFilters",
    "PackageCategoryFilters",
    "PackageAvailabilityFilters",
    "PackageReviewFilters",
]


class PackageFilters(BaseSchema):
    """
    Filter set for querying Package listings.

    All fields are optional. Combine freely — the repository applies
    them as AND conditions on the underlying query.
    """

    category_id: uuid.UUID | None = Field(
        default=None, description="Filter by parent category"
    )
    occasion_id: uuid.UUID | None = Field(
        default=None, description="Filter to packages linked to this occasion"
    )
    status: PackageStatus | None = Field(
        default=None, description="Filter by publication status"
    )
    is_featured: bool | None = Field(
        default=None, description="Return only featured (or non-featured) packages"
    )
    is_customizable: bool | None = Field(
        default=None, description="Return only customisable packages"
    )
    min_price: MoneyAmount | None = Field(
        default=None, description="Minimum base_price (inclusive)"
    )
    max_price: MoneyAmount | None = Field(
        default=None, description="Maximum base_price (inclusive)"
    )
    min_rating: Decimal | None = Field(
        default=None,
        ge=Decimal("1"),
        le=Decimal("5"),
        decimal_places=1,
        description="Filter packages with average_rating >= this value",
    )
    currency: Currency | None = Field(
        default=None, description="Return only packages priced in this currency"
    )
    search: str | None = Field(
        default=None,
        max_length=200,
        description="Full-text search against name and short_description",
    )
    city: str | None = Field(
        default=None,
        max_length=200,
        description="City slug to filter packages (e.g. 'noida', 'mumbai'). "
                    "Returns packages whose city_slug matches exactly.",
    )
    min_guests: int | None = Field(
        default=None, ge=1, description="Package can accommodate at least this many guests"
    )
    max_guests: int | None = Field(
        default=None, ge=1, description="Package max_guests is at most this value"
    )

    @model_validator(mode="after")
    def validate_price_range(self) -> "PackageFilters":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must be ≤ max_price")
        return self


class PackageCategoryFilters(BaseSchema):
    """Filter set for querying PackageCategory records."""

    is_active: bool | None = Field(
        default=None, description="Return only active (or inactive) categories"
    )
    search: str | None = Field(
        default=None, max_length=200, description="Search against name"
    )


class PackageAvailabilityFilters(BaseSchema):
    """Filter set for querying PackageAvailability slots."""

    package_id: uuid.UUID | None = Field(
        default=None, description="Filter slots for a specific package"
    )
    from_date: date | None = Field(
        default=None, description="Return slots on or after this date"
    )
    to_date: date | None = Field(
        default=None, description="Return slots on or before this date"
    )
    is_available: bool | None = Field(
        default=None, description="Return only available (or blocked) slots"
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "PackageAvailabilityFilters":
        if (
            self.from_date is not None
            and self.to_date is not None
            and self.from_date > self.to_date
        ):
            raise ValueError("from_date must be ≤ to_date")
        return self


class PackageReviewFilters(BaseSchema):
    """Filter set for querying PackageReview records."""

    package_id: uuid.UUID | None = Field(
        default=None, description="Reviews for a specific package"
    )
    reviewer_id: uuid.UUID | None = Field(
        default=None, description="Reviews submitted by a specific user"
    )
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    is_published: bool | None = Field(
        default=None, description="Return only published (or unpublished) reviews"
    )
    is_verified: bool | None = Field(default=None)
