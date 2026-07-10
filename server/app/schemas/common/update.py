"""Update (PATCH request body) schemas for the common/platform domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import BaseSchema, Latitude, Longitude
from app.models.enums import BannerType, BannerTargetAudience


class StateUpdate(BaseSchema):
    """Admin: update a state record."""

    name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class CityUpdate(BaseSchema):
    """Admin: update a city record."""

    name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    is_tier_1: bool | None = None
    is_tier_2: bool | None = None
    latitude: Latitude = None
    longitude: Longitude = None
    display_order: int | None = Field(default=None, ge=0)


class BannerUpdate(BaseSchema):
    """Admin: update a banner record."""

    title: str | None = Field(default=None, max_length=300)
    subtitle: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(default=None, max_length=2048)
    mobile_image_url: str | None = Field(default=None, max_length=2048)
    action_url: str | None = Field(default=None, max_length=2048)
    banner_type: BannerType | None = None
    target_audience: BannerTargetAudience | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class FAQUpdate(BaseSchema):
    """Admin: update an FAQ entry."""

    question: str | None = Field(default=None, max_length=500)
    answer: str | None = None
    category: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class AppSettingUpdate(BaseSchema):
    """Admin: update an application setting value."""

    value: str | None = None
    description: str | None = None
    is_public: bool | None = None
    is_editable: bool | None = None


class TermsUpdate(BaseSchema):
    """Admin: update a terms & conditions version."""

    content: str | None = None
    is_active: bool | None = None
    effective_from: datetime | None = None
    summary: str | None = None


class PrivacyPolicyUpdate(BaseSchema):
    """Admin: update a privacy policy version."""

    content: str | None = None
    is_active: bool | None = None
    effective_from: datetime | None = None
    summary: str | None = None
