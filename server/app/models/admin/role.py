"""
AdminRole — RBAC role definition for admin panel users.

Roles group permissions into named bundles that can be assigned to admin accounts.
The platform ships with a set of built-in system roles that cover the
organisational chart of a typical Tyohaar operations team:

    super_admin       — Full access to everything, including role management.
    operations_manager— Booking fulfilment, vendor assignment, SLA management.
    finance_manager   — Payments, settlements, refunds, invoicing.
    support_agent     — Support tickets, basic customer/vendor data lookup.
    vendor_manager    — Vendor onboarding, KYC review, account management.
    marketing_manager — Banners, FAQs, coupons, notifications.
    analytics_viewer  — Read-only access to reports and dashboards.

System roles (`is_system = True`) cannot be deleted or have their `slug`
changed.  New permissions CAN be added to or removed from system roles.

Custom roles can be created freely by super_admin users to support evolving
org structures without requiring a code deployment.

`priority_rank` enforces a hierarchy: a role with rank=1 has higher authority
than rank=100.  No admin can modify or assign roles with a lower rank number
than their own.  Super admin is typically rank=1.

`is_super_admin = True` bypasses all permission checks — the role implicitly
grants all current and future permissions without needing explicit entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import AuditMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.admin.admin import Admin
    from app.models.admin.role_permission import AdminRolePermission


class AdminRole(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    """
    A named permission bundle assigned to admin users.

    Permission check algorithm:
        1. Load admin.role.
        2. If role.is_super_admin → allow all.
        3. Otherwise, check role.permissions for a matching (resource, action) pair.
        4. If found and permission.is_active → allow.  Else → deny.

    Soft-delete is used instead of hard-delete so that historical AuditLog
    entries that reference a role remain interpretable after the role is retired.

    `slug` is stable across environments and used in code-level permission
    checks (e.g. `require_role("finance_manager")`).  Never change slugs for
    system roles.
    """

    __tablename__ = "admin_roles"

    __table_args__ = (
        UniqueConstraint("name", name="uq_admin_roles_name"),
        UniqueConstraint("slug", name="uq_admin_roles_slug"),
        Index("ix_admin_roles_is_active", "is_active"),
        Index("ix_admin_roles_is_system", "is_system"),
        Index("ix_admin_roles_priority_rank", "priority_rank"),
        CheckConstraint("priority_rank > 0", name="ck_admin_roles_priority_rank_positive"),
        CheckConstraint(
            "NOT (is_super_admin = true AND is_system = false)",
            name="ck_admin_roles_super_admin_must_be_system",
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Display name of the role (e.g. 'Finance Manager', 'Support Agent')",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment=(
            "Machine-readable identifier used in code-level checks "
            "(e.g. 'finance_manager', 'super_admin'). Never change for system roles."
        ),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of what this role can do",
    )

    # ── Configuration ─────────────────────────────────────────────────────────

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True = platform-seeded role. Cannot be deleted or have its slug changed. "
            "Permissions can still be added or removed."
        ),
    )

    is_super_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True bypasses all permission checks. The role grants implicit full access "
            "to all current and future resources. Must be a system role."
        ),
    )

    priority_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment=(
            "Hierarchy rank. Lower value = higher authority. "
            "An admin cannot assign or modify roles with a lower rank than their own."
        ),
    )

    # ── Visibility ────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False disables the role — admins assigned it lose all access",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    permissions: Mapped[list[AdminRolePermission]] = relationship(
        "AdminRolePermission",
        back_populates="role",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    admins: Mapped[list[Admin]] = relationship(
        "Admin",
        back_populates="role",
        lazy="noload",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:
        return (
            f"<AdminRole id={self.id} slug={self.slug!r} "
            f"is_super_admin={self.is_super_admin} rank={self.priority_rank}>"
        )
