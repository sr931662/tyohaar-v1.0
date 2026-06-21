"""
AdminRolePermission — junction table linking roles to their granted permissions.

This is a standard many-to-many join table between AdminRole and AdminPermission,
with two enhancements:

1. `conditions` JSONB: optional scope restrictions that narrow when the
   permission is effective.  Examples:
       {"department": "finance"}  — finance role only grants payment:read
                                    to members of the finance department.
       {"own_records_only": true} — support agent can only update tickets
                                    they are assigned to.
   Conditions are evaluated by the permission service at check time.
   NULL = no conditions; permission applies unconditionally.

2. `granted_at` / `granted_by_id`: audit trail of who granted which permission
   to which role.  The AuditMixin `created_by_id` covers this, but the
   dedicated `granted_by_id` provides a semantically clearer FK-free field
   that mirrors the broader audit pattern used in the project.

Design:
- CASCADE on both FKs: removing a role or permission cleans up all related
  junction rows automatically.
- Unique constraint on (role_id, permission_id): a permission can only be
  granted to a role once (duplicate grants are idempotent in the service layer).
- No soft-delete: removing a role-permission link is a hard delete.  The
  AuditLog captures every grant/revoke event for compliance.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.role import AdminRole
    from app.models.admin.permission import AdminPermission


class AdminRolePermission(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """
    A single permission grant: one role ← one permission.

    The effective permission set for an admin is:
        SELECT p.resource, p.action
        FROM admin_role_permissions rp
        JOIN admin_permissions p ON p.id = rp.permission_id
        WHERE rp.role_id = :role_id
          AND p.is_active = true;

    For roles where `is_super_admin = True`, this query is skipped entirely —
    the role service grants all permissions implicitly.

    `conditions` (optional) is evaluated by the permission service as a filter
    on the request context.  The schema of `conditions` is validated by the
    service layer, not the DB.  Unknown keys are ignored (permissive evaluation).
    """

    __tablename__ = "admin_role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_id",
            name="uq_admin_role_permissions_role_permission",
        ),
        Index("ix_admin_role_permissions_role_id", "role_id"),
        Index("ix_admin_role_permissions_permission_id", "permission_id"),
    )

    # ── Core ──────────────────────────────────────────────────────────────────

    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="CASCADE"),
        nullable=False,
        comment="The role being granted this permission",
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_permissions.id", ondelete="CASCADE"),
        nullable=False,
        comment="The permission being granted to the role",
    )

    # ── Scope Conditions ──────────────────────────────────────────────────────

    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Optional JSONB conditions that further restrict when this permission applies. "
            "Evaluated by the permission service at check time. "
            'Examples: {"department": "finance"}, {"own_records_only": true}. '
            "NULL = unconditional grant."
        ),
    )

    # ── Grant Audit ───────────────────────────────────────────────────────────

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when this permission was granted to the role",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    role: Mapped[AdminRole] = relationship(
        "AdminRole",
        back_populates="permissions",
        lazy="noload",
    )

    permission: Mapped[AdminPermission] = relationship(
        "AdminPermission",
        back_populates="role_permissions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<AdminRolePermission id={self.id} "
            f"role_id={self.role_id} permission_id={self.permission_id}>"
        )
