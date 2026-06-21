"""
Reusable SQLAlchemy column mixins for Tyohaar models.

Each mixin is designed to be independently composable with no inter-mixin
dependencies. Models may combine any subset without field conflicts.

Inheritance order matters in Python MRO — always place mixins before Base:

    class MyModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
        __tablename__ = "my_models"

Column declaration order in the final DDL follows Python's MRO left-to-right,
so mixins listed first appear earlier in the table definition.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """UUID v4 primary key.

    Preferred over auto-increment integers because:
    - Non-guessable: prevents enumeration attacks on API endpoints.
    - Globally unique: safe for distributed systems and cross-DB merges.
    - Generated client-side: IDs can be assigned before DB insert (useful
      for idempotent APIs and optimistic UI patterns).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID v4 primary key",
    )


class TimestampMixin:
    """Automatic created_at / updated_at audit timestamps.

    Both columns use server-side defaults so they are populated correctly
    even on raw SQL inserts and bulk operations that bypass the ORM.

    `updated_at` is refreshed by the DB trigger equivalent `onupdate`;
    in async SQLAlchemy this fires on ORM-level UPDATE statements.
    For raw SQL updates, a DB-level trigger should be added separately.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="UTC timestamp when the record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="UTC timestamp of the last ORM-level update",
    )


class SoftDeleteMixin:
    """Non-destructive deletion via a nullable deleted_at timestamp.

    A record is considered deleted when deleted_at IS NOT NULL.
    All active-record queries must filter: WHERE deleted_at IS NULL.

    For high-traffic tables, add a partial index per model:

        __table_args__ = (
            Index(
                "ix_<table>_not_deleted",
                "id",
                postgresql_where=text("deleted_at IS NULL"),
            ),
        )

    Never expose deleted records in public API responses.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Set to mark the record as soft-deleted. NULL means active.",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ActiveStatusMixin:
    """Boolean active flag for quick enable/disable without deletion.

    Use alongside SoftDeleteMixin for layered control:
    - is_active = False: temporarily disabled, fully reversible by admin.
    - deleted_at IS NOT NULL: permanently soft-deleted.

    Index is included because is_active is almost always part of WHERE clauses.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="False disables the record without deleting it",
    )


class CreatedByMixin:
    """Tracks which user (or system process) created this record.

    Stored as a bare UUID rather than a FK to avoid circular imports between
    model packages and to allow system-generated UUIDs (cron, migrations, seeds)
    that may not correspond to a real users row.
    """

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the user or system actor who created this record",
    )


class UpdatedByMixin:
    """Tracks which user (or system process) last modified this record."""

    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the user or system actor who last updated this record",
    )


class AuditMixin(CreatedByMixin, UpdatedByMixin):
    """Combined created_by + updated_by actor audit trail.

    Convenience mixin equivalent to inheriting both
    CreatedByMixin and UpdatedByMixin. Pair with TimestampMixin
    for a full four-field audit block (who + when).
    """

    pass


class VersionMixin:
    """Optimistic concurrency control via an integer version counter.

    Prevents lost-update anomalies when two transactions read and write
    the same row concurrently without row-level locking.

    To activate SQLAlchemy's built-in optimistic locking on a model,
    add the following to the model class (not this mixin, to allow opt-in):

        __mapper_args__ = {"version_id_col": version}

    The ORM will then automatically increment `version` on every UPDATE
    and raise `sqlalchemy.orm.exc.StaleDataError` if the version in the
    UPDATE WHERE clause doesn't match the current DB value.
    """

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Optimistic locking counter. Incremented on every update.",
    )


class NotesMixin:
    """Internal free-text notes field for admin and operations teams.

    This field must never be exposed in public-facing API responses.
    Suitable for CSR annotations, moderation comments, escalation notes,
    or any human-readable context that doesn't fit a structured column.
    """

    internal_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal ops/admin notes. Never expose via public API.",
    )


class MetadataMixin:
    """Flexible JSONB column for unstructured or extensible attributes.

    Use cases:
    - Feature flags scoped to a single entity.
    - Platform-specific attributes (iOS vs Android vs Web).
    - A/B test variant assignments.
    - Vendor-specific configuration that doesn't warrant a schema column.
    - Rapid prototyping before a column is formally added.

    For frequently queried JSONB paths, add a GIN index on the model:

        __table_args__ = (
            Index("ix_<table>_metadata_gin", "extra_metadata",
                  postgresql_using="gin"),
        )
    """

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Flexible JSONB bag for extensible, unstructured attributes",
    )
