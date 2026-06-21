"""
Query-parameter filter schemas for the occasions domain.

Used as FastAPI dependency injections. All fields are Optional.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.models.enums import OccasionCategory, CelebrationStatus

__all__ = [
    "CelebrationFilters",
    "OccasionFilters",
]


class CelebrationFilters(BaseSchema):
    """
    Filtering parameters for the celebration listing endpoint.

    Use from_date / to_date to restrict by celebration_date range.
    Use is_upcoming=True to return only celebrations whose date is in the future.
    """

    model_config = ConfigDict(populate_by_name=True)

    customer_id: uuid.UUID | None = Field(
        default=None,
        description="Return only celebrations belonging to this customer",
    )
    occasion_id: uuid.UUID | None = Field(
        default=None,
        description="Return only celebrations of this occasion type",
    )
    status: CelebrationStatus | None = Field(
        default=None,
        description="Filter by celebration lifecycle status",
    )
    from_date: date | None = Field(
        default=None,
        description="Return celebrations with celebration_date >= this date",
    )
    to_date: date | None = Field(
        default=None,
        description="Return celebrations with celebration_date <= this date",
    )
    is_upcoming: bool | None = Field(
        default=None,
        description="If True, return only future celebrations (celebration_date >= today)",
    )


class OccasionFilters(BaseSchema):
    """
    Filtering parameters for the occasion catalogue endpoint.

    Supports category filtering, active/featured flags, and text search.
    """

    model_config = ConfigDict(populate_by_name=True)

    category: OccasionCategory | None = Field(
        default=None,
        description="Filter by occasion category bucket",
    )
    is_active: bool | None = Field(
        default=None,
        description="Return only active (True) or inactive (False) occasions",
    )
    is_featured: bool | None = Field(
        default=None,
        description="Return only featured occasions (displayed on home screen)",
    )
    search: str | None = Field(
        default=None,
        max_length=200,
        description="Full-text search on occasion name and description",
    )
