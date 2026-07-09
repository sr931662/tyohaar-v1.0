"""
Feedback domain — filter query parameter schema (admin list view).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import FeedbackCategory
from app.schemas.base import BaseSchema

__all__ = ["FeedbackFilters"]


class FeedbackFilters(BaseSchema):
    category: FeedbackCategory | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    is_reviewed: bool | None = Field(default=None)
    from_date: datetime | None = Field(default=None)
    to_date: datetime | None = Field(default=None)
