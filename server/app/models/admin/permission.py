"""
AdminPermission — granular RBAC permission definition.

Every controllable action on every platform resource is represented as a
Permission row.  Permissions are the atoms of the RBAC system; roles are
bundles of permissions.

A Permission is uniquely identified by its (resource, action) pair.
The `code` column is the canonical machine key:
    resource:action → e.g. "bookings:approve", "users:export"

`MANAGE` action is a meta-permission that grants all sub-actions on the
resource.  When checking if an admin has "bookings:update", the permission
service also accepts "bookings:manage" as a match.

Platform-seeded permissions (`is_system = True`) cover every resource ×
action combination defined in the PermissionResource and PermissionAction
enums.  Custom permissions can be added by super_admin for future use cases.

`group` enables the admin panel to render permissions in logical sections
(mirrors the resource name but allows UI-level customisation):
    "Booking Management", "User Management", "Financial Operations", etc.

Permissions are additive: an admin's effective permission set is the union of
all permissions across all their assigned roles.  There is no explicit deny;
to restrict access, remove the role or permission assignment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import PermissionAction, PermissionResource
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.role_permission import AdminRolePermission


class AdminPermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single granular RBAC permission.

    Unique identity: (resource, action) pair.
    Canonical machine key: `code` = "{resource}:{action}" (e.g. "bookings:approve").

    Permission check (service layer):
        1. Load all AdminRolePermission rows for the admin's role.
        2. Check if any row has (resource=requested_resource, action=requested_action)
           OR (resource=requested_resource, action=MANAGE).
        3. If the admin's role.is_super_admin → always allow.

    System permissions (`is_system = True`) are seeded at deploy time and
    cannot be deleted, as they may be referenced by existing role assignments.
    Deactivating a system permission (`is_active = False`) immediately
    revokes it from all roles that hold it.
    """

    __tablename__ = "admin_permissions"

    __table_args__ = (
        UniqueConstraint("code", name="uq_admin_permissions_code"),
        UniqueConstraint("resource", "action", name="uq_admin_permissions_resource_action"),
        Index("ix_admin_permissions_resource", "resource"),
        Index("ix_admin_permissions_action", "action"),
        Index("ix_admin_permissions_group", "group"),
        Index("ix_admin_permissions_is_active", "is_active"),
        Index("ix_admin_permissions_is_system", "is_system"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable permission name (e.g. 'Approve Bookings', 'Export Users')",
    )

    code: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        comment=(
            "Machine key in 'resource:action' format (e.g. 'bookings:approve'). "
            "Used in API permission guard decorators."
        ),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what this permission allows and any caveats",
    )

    # ── RBAC Classification ───────────────────────────────────────────────────

    resource: Mapped[PermissionResource] = mapped_column(
        SAEnum(PermissionResource, name="permission_resource", native_enum=False),
        nullable=False,
        comment="Platform entity type this permission governs",
    )

    action: Mapped[PermissionAction] = mapped_column(
        SAEnum(PermissionAction, name="permission_action", native_enum=False),
        nullable=False,
        comment="Verb describing what the holder can do on the resource",
    )

    # ── UI Grouping ───────────────────────────────────────────────────────────

    group: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment=(
            "UI section label for admin panel permission lists "
            "(e.g. 'Booking Management', 'Financial Operations', 'User Management')"
        ),
    )

    # ── Platform Controls ─────────────────────────────────────────────────────

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True = seeded by the platform; cannot be deleted. "
            "All (resource, action) combinations from the enums are system permissions."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "False immediately revokes this permission across all role assignments. "
            "Use to emergency-disable sensitive capabilities platform-wide."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    role_permissions: Mapped[list[AdminRolePermission]] = relationship(
        "AdminRolePermission",
        back_populates="permission",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AdminPermission id={self.id} code={self.code!r} "
            f"is_active={self.is_active}>"
        )
