"""
Feedback domain — response (output) schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.models.enums import FeedbackCategory
from app.schemas.base import BaseSchema

__all__ = ["FeedbackResponse"]


class FeedbackResponse(BaseSchema):
    """Field names mirror the Feedback model exactly — no aliasing needed."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    rating: int
    category: FeedbackCategory
    comments: str | None = None
    app_version: str | None = None
    is_reviewed: bool
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
