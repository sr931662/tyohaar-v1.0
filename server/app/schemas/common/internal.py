"""Internal/admin schemas for the common/platform domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema
from app.models.enums import BannerType, BannerTargetAudience


class BannerInternal(BaseSchema):
    """Full banner record for admin use — includes click analytics."""

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
    click_count: int = 0  # INTERNAL — analytics counter, not exposed publicly
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AppSettingInternal(BaseSchema):
    """All app settings regardless of is_public flag — admin/ops use only."""

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


class FAQFeedbackUpdate(BaseSchema):
    """Track customer helpful/not-helpful votes on an FAQ."""

    is_helpful: bool = Field(description="True = helpful, False = not helpful")
