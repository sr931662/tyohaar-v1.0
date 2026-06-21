"""Create (POST request body) schemas for the common/platform domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, Latitude, Longitude
from app.models.enums import BannerType, BannerTargetAudience


class StateCreate(BaseSchema):
    """Admin: create a new state/UT record."""

    name: str = Field(max_length=100)
    code: str = Field(max_length=10, description="State code e.g. MH, DL")
    country_code: str = Field(default="IN", max_length=2)
    is_active: bool = True
    display_order: int = Field(default=0, ge=0)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


class CityCreate(BaseSchema):
    """Admin: create a new city record."""

    state_id: uuid.UUID
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100, pattern=r"^[a-z0-9-]+$")
    is_active: bool = True
    is_tier_one: bool = False
    latitude: Latitude = None
    longitude: Longitude = None
    display_order: int = Field(default=0, ge=0)


class BannerCreate(BaseSchema):
    """Admin: create a promotional or informational banner."""

    title: str = Field(max_length=300)
    subtitle: str | None = Field(default=None, max_length=500)
    image_url: str = Field(max_length=2048)
    mobile_image_url: str | None = Field(default=None, max_length=2048)
    action_url: str | None = Field(default=None, max_length=2048)
    banner_type: BannerType
    target_audience: BannerTargetAudience = BannerTargetAudience.ALL
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    display_order: int = Field(default=0, ge=0)


class FAQCreate(BaseSchema):
    """Admin: create a platform FAQ entry."""

    question: str = Field(max_length=500)
    answer: str = Field(min_length=1)
    category: str = Field(max_length=100, description="e.g. booking, payment, vendor")
    is_active: bool = True
    display_order: int = Field(default=0, ge=0)


class AppSettingCreate(BaseSchema):
    """Admin: create a named application setting."""

    key: str = Field(max_length=200)
    value: str
    value_type: str = Field(
        max_length=50,
        description="Type hint for the value: string, integer, boolean, json, float",
    )
    description: str | None = None
    is_public: bool = Field(
        default=False,
        description="If True, this setting is readable by the app without authentication",
    )
    is_editable: bool = True
    category: str | None = Field(default=None, max_length=100)


class TermsCreate(BaseSchema):
    """Admin: publish a new terms & conditions version."""

    version: str = Field(max_length=20, description="Semantic version e.g. 1.0.0")
    content: str = Field(min_length=1, description="Full HTML or Markdown content")
    effective_from: datetime
    summary: str | None = Field(default=None, description="Short summary of changes for users")
    is_active: bool = False


class PrivacyPolicyCreate(BaseSchema):
    """Admin: publish a new privacy policy version."""

    version: str = Field(max_length=20)
    content: str = Field(min_length=1)
    effective_from: datetime
    summary: str | None = None
    is_active: bool = False


# Aliases consumed by the common controller
AppSettingUpsert = AppSettingCreate
TermsVersionCreate = TermsCreate
