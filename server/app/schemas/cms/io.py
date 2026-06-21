"""Import / Export Schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Import ────────────────────────────────────────────────────────────────────

IMPORTABLE_ENTITIES = [
    "vendors", "customers", "packages", "services", "categories",
    "cities", "states", "memberships", "coupons", "faqs",
    "notification_templates", "settings",
]

EXPORT_FORMATS = ["XLSX", "CSV", "JSON"]


class ImportValidateRequest(_Base):
    entity_type: str = Field(..., description="One of: " + ", ".join(IMPORTABLE_ENTITIES))
    is_dry_run: bool = Field(default=False)


class RowError(_Base):
    row: int
    field: str | None = None
    message: str
    value: Any = None


class ImportPreviewRow(_Base):
    row: int
    data: dict[str, Any]
    is_valid: bool
    is_duplicate: bool
    errors: list[RowError]
    action: str = Field(description="INSERT | UPDATE | SKIP")


class ImportPreviewResponse(_Base):
    entity_type: str
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    preview_rows: list[ImportPreviewRow]
    column_mapping: dict[str, str]
    sample_errors: list[RowError]
    can_proceed: bool


class ImportExecuteRequest(_Base):
    log_id: uuid.UUID = Field(..., description="ID from the validate step")
    overwrite_duplicates: bool = Field(default=False)


class ImportLogResponse(_Base):
    id: uuid.UUID
    admin_id: uuid.UUID | None = None
    entity_type: str
    original_filename: str
    status: str
    is_dry_run: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    inserted_rows: int
    updated_rows: int
    skipped_rows: int
    progress_pct: float
    error_summary: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ImportUndoResponse(_Base):
    log_id: uuid.UUID
    rows_deleted: int
    status: str
    message: str


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(_Base):
    entity_type: str
    format: str = Field(default="XLSX", description="XLSX | CSV | JSON")
    filters: dict[str, Any] | None = None
    selected_ids: list[str] | None = Field(
        default=None, description="If provided, export only these records"
    )
    column_selection: list[str] | None = Field(
        default=None, description="Subset of columns to include; null = all"
    )
    date_range_from: datetime | None = None
    date_range_to: datetime | None = None
    is_scheduled: bool = Field(default=False)
    schedule_cron: str | None = Field(default=None, description="Cron expression for scheduled exports")


class ExportLogResponse(_Base):
    id: uuid.UUID
    admin_id: uuid.UUID | None = None
    entity_type: str
    format: str
    status: str
    filters: dict[str, Any] | None = None
    row_count: int
    file_size_bytes: int | None = None
    download_url: str | None = None
    expires_at: datetime | None = None
    is_scheduled: bool
    schedule_cron: str | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ExportTriggerResponse(_Base):
    log_id: uuid.UUID
    status: str
    message: str
    estimated_rows: int | None = None
