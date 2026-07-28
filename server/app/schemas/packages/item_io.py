"""
Bulk import/export result schemas for vendor package items and common items.

Deliberately separate from app.schemas.cms.io — that engine is admin-scoped
with a dry-run/preview/rollback workflow; vendor item import is a simpler,
synchronous upsert-by-name operation with no admin-review step.
"""

from __future__ import annotations

from typing import Literal

from app.schemas.base import BaseSchema


class ItemImportRowResult(BaseSchema):
    row: int
    action: Literal["created", "updated", "error"]
    name: str | None = None
    error: str | None = None


class ItemImportResult(BaseSchema):
    total_rows: int
    created: int
    updated: int
    errors: int
    row_results: list[ItemImportRowResult]
