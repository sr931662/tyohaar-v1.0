"""
Shared nested types and enum re-exports for the packages domain.

Import from this module whenever you need package-related sub-objects
(e.g. price tiers) or enum values in other package schema files.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema
from app.models.enums import (
    Currency,
    PackagePricingType,
    PackageStatus,
)

__all__ = [
    # nested types
    "PriceTierSchema",
    # enums
    "Currency",
    "PackagePricingType",
    "PackageStatus",
]


class PriceTierSchema(BaseSchema):
    """
    A single step in a tiered-pricing schedule.

    Represents the price that applies when guest count falls within
    the [min_guests, max_guests] inclusive range.
    """

    min_guests: int = Field(ge=1, description="Minimum guest count for this tier")
    max_guests: int | None = Field(
        default=None,
        description="Maximum guest count for this tier (None = unlimited)",
    )
    price: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Price for this tier in the package currency",
    )
    label: str | None = Field(
        default=None,
        max_length=100,
        description="Human-readable tier label, e.g. '50–100 guests'",
    )

    def model_post_init(self, __context: object) -> None:
        if self.max_guests is not None and self.max_guests < self.min_guests:
            raise ValueError("max_guests must be >= min_guests")
