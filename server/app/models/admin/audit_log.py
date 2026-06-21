"""
AuditLog — immutable chronological record of every admin-initiated action.

The audit log is the compliance backbone of the admin panel.  Every state
change made by an admin (or triggered by an automated system process) must
produce exactly one AuditLog row.  Rows are NEVER updated or deleted after
creation — they are append-only.

Immutability is enforced at the DB layer by revoked DELETE/UPDATE privileges
on the `audit_logs` table for the application role in production.

Use cases:
- Compliance: who approved a refund, who changed a vendor's KYC status.
- Security forensics: trace admin actions after a suspected breach.
- Dispute resolution: show the exact state before/after a booking change.
- Regulatory: DPDPA / GDPR data access logs (view_sensitive action).
- Operational debugging: replay admin actions to reproduce bugs.

Polymorphic target entity:
- `entity_type` (e.g. "booking", "vendor", "user", "payment") + `entity_id`
  together identify the affected record.
- `entity_display` is a human-readable snapshot of the entity at action time
  (e.g. "Booking TYH-20240615-001234", "Vendor: Shree Decorators").
  Stored as a snapshot because the target entity may change its display
  representation in the future.

Change tracking:
- `before_value` and `after_value` are JSONB snapshots of the row state
  before and after the action.  For CREATE: before_value = NULL.
  For DELETE: after_value = NULL.  For UPDATE: both are populated.
- `changed_fields` is a PostgreSQL ARRAY of field names that changed,
  allowing fast filtering without parsing JSONB diffs.

Request context:
- `ip_address`: the IP that made the admin API request.
- `user_agent`: the browser/client that made the request.
- `request_id`: correlation ID from the X-Request-ID header for log correlation.
- `endpoint`: the API path (e.g. "/admin/bookings/{id}/approve").
- `http_method`: HTTP verb of the triggering request.

Actor types:
- "admin":   a human admin user identified by actor_id.
- "system":  automated platform process (cron job, webhook handler).
- "cron":    scheduled background task.
- "api_key": machine-to-machine API access.
"""

from __future__ import annotations

import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AuditAction
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin import Admin


_VALID_ACTOR_TYPES = ("admin", "system", "cron", "api_key")


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single immutable audit entry capturing one admin or system action.

    IMMUTABILITY CONTRACT:
        This table must have NO UPDATE or DELETE privileges granted to the
        application DB role in production.  All rows are permanent.
        To 'undo' an admin action, create a new reversal action row.

    Index strategy:
    - (actor_id, created_at): the most common query — "all actions by this admin
      sorted by time."
    - (entity_type, entity_id): "all actions on this specific booking/vendor/etc."
    - (action): "all approve actions platform-wide."
    - (created_at): chronological audit trail queries.
    - (is_sensitive): compliance filtering for PII access reports.

    Retention policy (enforced by a background job, not by DB):
        - Standard audit logs: retained for 3 years.
        - Sensitive logs (is_sensitive = True): retained for 7 years.
        - Never deleted for financial or KYC-related actions.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity_type", "entity_type"),
        Index("ix_audit_logs_entity_type_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_is_sensitive", "is_sensitive"),
        Index("ix_audit_logs_is_successful", "is_successful"),
        CheckConstraint(
            f"actor_type IN {_VALID_ACTOR_TYPES!r}",
            name="ck_audit_logs_actor_type_valid",
        ),
    )

    # ── Actor ─────────────────────────────────────────────────────────────────

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Admin who performed the action. "
            "NULL for system-generated entries (cron, webhooks, automated processes). "
            "SET NULL on Admin deletion to preserve audit trail integrity."
        ),
    )

    actor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="admin",
        comment=(
            "Classification of the actor. "
            "One of: 'admin', 'system', 'cron', 'api_key'. "
            "Checked via constraint ck_audit_logs_actor_type_valid."
        ),
    )

    actor_display: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment=(
            "Snapshot of the actor's display name at action time "
            "(e.g. 'Priya S. (Finance Manager)'). "
            "Preserved even if the admin account is later deactivated or renamed."
        ),
    )

    # ── Action ────────────────────────────────────────────────────────────────

    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="audit_action", native_enum=False),
        nullable=False,
        comment="Type of action performed",
    )

    # ── Target Entity (polymorphic) ───────────────────────────────────────────

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Type of the affected entity. "
            "Matches the domain name (e.g. 'booking', 'vendor', 'user', 'payment', "
            "'admin_role', 'app_setting', 'coupon')."
        ),
    )

    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the affected entity. NULL for list-level or schema-level actions "
            "(e.g. 'export all users', 'maintenance mode toggle')."
        ),
    )

    entity_display: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "Human-readable snapshot of the entity at action time. "
            "Examples: 'Booking TYH-001234', 'Vendor: Shree Decorators (id=...)'. "
            "Preserved for readability after the entity name changes."
        ),
    )

    # ── Change Tracking ───────────────────────────────────────────────────────

    before_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "JSON snapshot of the entity state BEFORE the action. "
            "NULL for CREATE actions. "
            "Sensitive fields must be masked before storing (handled by service layer)."
        ),
    )

    after_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "JSON snapshot of the entity state AFTER the action. "
            "NULL for DELETE / SOFT_DELETE actions."
        ),
    )

    changed_fields: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment=(
            "List of field names that changed in an UPDATE action. "
            "Allows filtered queries without parsing full JSONB diffs "
            "(e.g. find all audit logs where 'status' changed)."
        ),
    )

    # ── Request Context ───────────────────────────────────────────────────────

    ip_address: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="IPv4 or IPv6 address of the admin making the request",
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="User-Agent header from the admin panel HTTP request",
    )

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "Admin session UUID at the time of the action. "
            "Bare UUID — no FK to avoid coupling with the auth domain."
        ),
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "Correlation ID from the X-Request-ID header. "
            "Links this audit entry to application logs and APM traces."
        ),
    )

    endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "API route that triggered this action "
            "(e.g. '/admin/bookings/{id}/approve')"
        ),
    )

    http_method: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="HTTP verb of the triggering request (GET, POST, PUT, PATCH, DELETE)",
    )

    # ── Outcome ───────────────────────────────────────────────────────────────

    is_successful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True when the action completed successfully. "
            "False for failed attempts (e.g. permission denied, validation error). "
            "Failed actions are still logged for security forensics."
        ),
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Error message or reason code when is_successful = False",
    )

    # ── Compliance Metadata ───────────────────────────────────────────────────

    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when this log entry involves PII access, financial data, "
            "or security-sensitive operations. "
            "Triggers extended retention and restricted visibility."
        ),
    )

    data_classification: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment=(
            "Data sensitivity classification for compliance reporting. "
            "Examples: 'pii', 'financial', 'kyc', 'internal'. NULL = general."
        ),
    )

    # ── Extra Context ─────────────────────────────────────────────────────────

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Additional context that does not fit the structured columns. "
            "Examples: bulk action counts, impersonation target user ID, "
            "export filters applied, custom notes from the action handler."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    actor: Mapped[Admin | None] = relationship(
        "Admin",
        back_populates="audit_logs",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"entity={self.entity_type}:{self.entity_id} "
            f"actor_id={self.actor_id} success={self.is_successful}>"
        )
