"""Response schemas for the common/platform domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field

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
    display_name: str
    slug: str
    is_active: bool
    is_tier_1: bool
    is_tier_2: bool
    is_serviceable: bool
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
    action_url: str | None = Field(default=None, validation_alias=AliasChoices("action_url", "cta_url"))
    banner_type: BannerType
    target_audience: BannerTargetAudience
    valid_from: datetime | None = Field(default=None, validation_alias=AliasChoices("valid_from", "display_start_at"))
    valid_until: datetime | None = Field(default=None, validation_alias=AliasChoices("valid_until", "display_end_at"))
    is_active: bool
    display_order: int
    created_at: datetime


class FAQResponse(BaseSchema):
    """FAQ entry response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    question: str
    answer: str
    category: str = Field(validation_alias=AliasChoices("category", "faq_category"))
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
    value: str | None = Field(default=None)
    value_type: str = Field(validation_alias=AliasChoices("value_type", "data_type"))


class AppSettingAdminResponse(BaseSchema):
    """Full app setting response for admin endpoints."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    key: str
    value: str | None = Field(default=None)
    value_type: str = Field(validation_alias=AliasChoices("value_type", "data_type"))
    description: str | None = None
    is_public: bool
    is_editable: bool
    category: str | None = Field(default=None, validation_alias=AliasChoices("category", "group"))
    created_at: datetime
    updated_at: datetime


class TermsResponse(BaseSchema):
    """Terms & conditions version response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    version: str
    title: str
    content: str
    status: str
    effective_date: date
    summary: str | None = None
    created_at: datetime


class PrivacyPolicyResponse(BaseSchema):
    """Privacy policy version response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    version: str
    title: str
    content: str
    status: str
    effective_date: date
    summary: str | None = None
    created_at: datetime


class CancellationPolicyResponse(BaseSchema):
    """Cancellation & refund policy version response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    version: str
    title: str
    content: str
    status: str
    effective_date: date
    summary: str | None = None
    created_at: datetime


# Alias consumed by the common controller
TermsVersionResponse = TermsResponse


class FinanceSettingsResponse(BaseSchema):
    """Platform finance switches. Public: the apps need them to price a plan."""

    gst_enabled: bool = False
    gst_rate_pct: int = 18


class FinanceSettingsUpdate(BaseSchema):
    """Admin: change the finance switches."""

    gst_enabled: bool
