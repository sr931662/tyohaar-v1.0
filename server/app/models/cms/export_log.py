"""Export log — records every data export request."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ExportLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks every export task — scheduled or on-demand."""

    __tablename__ = "cms_export_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','COMPLETED','FAILED','EXPIRED')",
            name="ck_export_logs_status",
        ),
        CheckConstraint(
            "format IN ('XLSX','CSV','JSON')",
            name="ck_export_logs_format",
        ),
        Index("ix_export_logs_admin_id", "admin_id"),
        Index("ix_export_logs_entity_type", "entity_type"),
        Index("ix_export_logs_status", "status"),
        Index("ix_export_logs_created_at", "created_at"),
    )

    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False, default="XLSX", server_default="XLSX")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")

    # Applied filters as JSON
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    selected_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    column_selection: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Result
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    file_storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    schedule_cron: Mapped[str | None] = mapped_column(String(64), nullable=True)
