"""Filter/query-parameter schemas for common/platform domain list endpoints."""

from __future__ import annotations

import uuid
from pydantic import Field
from app.schemas.base import BaseSchema
from app.models.enums import BannerType, BannerTargetAudience


class CityFilters(BaseSchema):
    """Query parameters for listing cities."""

    state_id: uuid.UUID | None = None
    is_active: bool | None = None
    is_tier_one: bool | None = None
    search: str | None = Field(default=None, description="Search city by name (case-insensitive)")


class BannerFilters(BaseSchema):
    """Query parameters for listing banners."""

    banner_type: BannerType | None = None
    target_audience: BannerTargetAudience | None = None
    is_active: bool | None = None
    from_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter valid_from >= from_date",
    )
    to_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter valid_until <= to_date",
    )


class FAQFilters(BaseSchema):
    """Query parameters for listing FAQs."""

    category: str | None = None
    is_active: bool | None = None
    search: str | None = Field(default=None, description="Search FAQ by question text")


class AppSettingFilters(BaseSchema):
    """Query parameters for listing app settings (admin endpoint)."""

    category: str | None = None
    is_public: bool | None = None
    is_editable: bool | None = None
    search: str | None = Field(default=None, description="Search by setting key")
