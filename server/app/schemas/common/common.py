"""Shared types for the common/platform domain."""

from __future__ import annotations

from typing import Annotated
from pydantic import Field
from app.models.enums import BannerType, BannerTargetAudience

# Re-export for convenience
__all__ = ["BannerType", "BannerTargetAudience", "LocalizedText"]

# Placeholder for future i18n — currently just a plain string
LocalizedText = Annotated[str, Field(description="Localized display text")]
