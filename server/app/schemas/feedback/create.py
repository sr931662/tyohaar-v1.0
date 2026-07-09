"""
Feedback domain — create (input) schema.
"""

from __future__ import annotations

from pydantic import Field

from app.models.enums import FeedbackCategory
from app.schemas.base import BaseSchema

__all__ = ["FeedbackCreate"]


class FeedbackCreate(BaseSchema):
    """
    Customer-facing input for submitting app feedback.

    The owning customer is always the authenticated caller (injected
    server-side from the auth token), never accepted from the request body.
    """

    rating: int = Field(ge=1, le=5, description="1-5 star rating.")
    category: FeedbackCategory = Field(description="What the feedback is about.")
    comments: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text comments.",
    )
    app_version: str | None = Field(
        default=None,
        max_length=20,
        description="Client app version, for triage context.",
    )
