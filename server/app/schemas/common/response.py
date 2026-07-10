"""Response schemas for the common/platform domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema, Latitude, Longitude
from app.models.enums import BannerType, BannerTargetAudience


class StateResponse(BaseSchema):
    """State/UT record response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    code: str
    country_code: str
    is_active: bool
    display_order: int


class CityResponse(BaseSchema):
    """City record response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    state_id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    is_tier_1: bool
    is_tier_2: bool
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    display_order: int


class BannerResponse(BaseSchema):
    """
    Promotional banner response.
    click_count is excluded — internal analytics metric.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    subtitle: str | None = None
    image_url: str
    mobile_image_url: str | None = None
    action_url: str | None = None
    banner_type: BannerType
    target_audience: BannerTargetAudience
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool
    display_order: int
    created_at: datetime


class FAQResponse(BaseSchema):
    """FAQ entry response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    question: str
    answer: str
    category: str
    is_active: bool
    display_order: int
    helpful_count: int
    not_helpful_count: int
    created_at: datetime


class AppSettingResponse(BaseSchema):
    """
    Public app setting response — only for settings with is_public=True.
    Returned without auth for app bootstrapping.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    key: str
    value: str
    value_type: str


class AppSettingAdminResponse(BaseSchema):
    """Full app setting response for admin endpoints."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    key: str
    value: str
    value_type: str
    description: str | None = None
    is_public: bool
    is_editable: bool
    category: str | None = None
    created_at: datetime
    updated_at: datetime


class TermsResponse(BaseSchema):
    """Terms & conditions version response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    version: str
    content: str
    is_active: bool
    effective_from: datetime
    summary: str | None = None
    created_at: datetime


class PrivacyPolicyResponse(BaseSchema):
    """Privacy policy version response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    version: str
    content: str
    is_active: bool
    effective_from: datetime
    summary: str | None = None
    created_at: datetime


# Alias consumed by the common controller
TermsVersionResponse = TermsResponse
