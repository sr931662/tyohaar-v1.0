"""Import log — tracks every bulk import operation for history and undo support."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import MetadataMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ImportLog(UUIDPrimaryKeyMixin, TimestampMixin, MetadataMixin, Base):
    """Records every import attempt with validation results and rollback data."""

    __tablename__ = "cms_import_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','VALIDATING','PREVIEW','PROCESSING','COMPLETED','FAILED','ROLLED_BACK')",
            name="ck_import_logs_status",
        ),
        CheckConstraint(
            "entity_type IN ('vendors','customers','packages','services','categories','cities','states','memberships','coupons','faqs','notification_templates','settings')",
            name="ck_import_logs_entity_type",
        ),
        Index("ix_import_logs_admin_id", "admin_id"),
        Index("ix_import_logs_entity_type", "entity_type"),
        Index("ix_import_logs_status", "status"),
        Index("ix_import_logs_created_at", "created_at"),
    )

    # ── Who/what ──────────────────────────────────────────────────────────────
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who initiated the import",
    )
    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Target entity being imported",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_storage_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Internal storage path of uploaded file",
    )

    # ── Execution state ───────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )
    is_dry_run: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        comment="True means validate + preview only, no writes",
    )

    # ── Row counts ────────────────────────────────────────────────────────────
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # ── Progress ──────────────────────────────────────────────────────────────
    progress_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    error_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured validation errors keyed by row number",
    )
    rollback_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Inserted IDs for rollback support",
    )
    started_at: Mapped[Any | None] = mapped_column(nullable=True)
    completed_at: Mapped[Any | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
