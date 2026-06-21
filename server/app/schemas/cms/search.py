"""Global Search Schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SearchResultItem(_Base):
    id: uuid.UUID | str
    entity_type: str
    title: str
    subtitle: str | None = None
    badge: str | None = None
    thumbnail_url: str | None = None
    url: str | None = None
    score: float | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


class SearchResultGroup(_Base):
    entity_type: str
    label: str
    total: int
    items: list[SearchResultItem]


class GlobalSearchResponse(_Base):
    query: str
    total_results: int
    took_ms: float
    groups: list[SearchResultGroup]


class GlobalSearchRequest(_Base):
    q: str = Field(..., min_length=1, max_length=255, description="Search query")
    entity_types: list[str] | None = Field(
        default=None,
        description="Filter to specific entity types; null = search all",
    )
    limit_per_group: int = Field(default=5, ge=1, le=20)
