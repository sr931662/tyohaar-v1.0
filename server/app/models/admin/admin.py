"""
Admin — an administrative user of the Tyohaar internal panel.

Every admin account is backed by a User record (1:1 via user_id).  The User
record holds authentication credentials and session management; the Admin record
extends it with role assignment, department context, access control flags, and
employment metadata.

Creating an admin account:
    1. Create or lookup the User record with role = UserRole.ADMIN or SUPER_ADMIN.
    2. Create the Admin record pointing to that User.
    3. Assign an AdminRole.

An admin inherits all platform auth mechanisms (OTP, MFA, session management)
from the Users domain.  `mfa_enforced = True` is the default for all admins
and must not be disabled without explicit policy justification.

Security controls:
- `ip_whitelist`: only IP addresses matching these CIDR ranges may authenticate.
  NULL = no IP restriction. Updated by ops team per admin onboarding policy.
- `can_impersonate`: allows the admin to view the app as a specific customer
  or vendor for debugging. Requires AuditLog entry on every impersonation session.
- `can_access_financials`: gates access to full payment amounts, bank details,
  and settlement records. Granted only to Finance department.
- `can_export_data`: gates bulk data export endpoints. Subject to approval workflow.

Self-referential org hierarchy:
- `reporting_to_id` enables org chart rendering in the admin panel.
- No cascade on delete: if a manager's account is deactivated, their direct
  reports' reporting_to_id is SET NULL rather than cascading.

`last_login_at` and `failed_login_count` are updated by the auth service
(not by this domain) for each admin login attempt.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AdminDepartment, AdminStatus
from app.models.mixins import (
    MetadataMixin,
    NotesMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.admin.role import AdminRole
    from app.models.admin.audit_log import AuditLog


class Admin(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, NotesMixin, MetadataMixin, Base):
    """
    An internal admin panel user with RBAC-controlled access.

    Relationship to User:
    - Every Admin has exactly one User account (user_id UNIQUE constraint).
    - Authentication (OTP, sessions, MFA) is handled entirely by the Users domain.
    - The Admin record adds: role, department, security flags, and audit trail.

    Lifecycle:
        INACTIVE (just created, awaiting onboarding)
        → ACTIVE  (onboarded, MFA configured)
        → SUSPENDED (security incident or policy violation)
        → DEACTIVATED (off-boarded; soft-deleted row preserved)

    `failed_login_count` and `account_locked_until` are maintained by the auth
    service.  After N consecutive failures (configured in AppSettings), the
    account is locked until the timestamp passes or an admin manually resets it.

    Org hierarchy:
    - `reporting_to_id` is a self-referential FK (SET NULL on manager deletion).
    - No maximum depth enforced; the UI limits display to 5 levels.
    """

    __tablename__ = "admins"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_admins_user_id"),
        UniqueConstraint("employee_id", name="uq_admins_employee_id"),
        UniqueConstraint("work_email", name="uq_admins_work_email"),
        Index("ix_admins_role_id", "role_id"),
        Index("ix_admins_admin_status", "admin_status"),
        Index("ix_admins_department", "department"),
        Index("ix_admins_reporting_to_id", "reporting_to_id"),
        Index("ix_admins_role_status", "role_id", "admin_status"),
        CheckConstraint(
            "failed_login_count >= 0",
            name="ck_admins_failed_login_count_non_negative",
        ),
    )

    # ── User Account Link ─────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        comment=(
            "FK to the User record that holds auth credentials for this admin. "
            "RESTRICT prevents deleting a User while an Admin record exists."
        ),
    )

    # ── Role ──────────────────────────────────────────────────────────────────

    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_roles.id", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "RBAC role that governs this admin's permissions. "
            "RESTRICT prevents deleting a role while admins are assigned to it."
        ),
    )

    # ── Profile ───────────────────────────────────────────────────────────────

    employee_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        comment="Internal HR employee identifier (e.g. 'TYH-001', 'EMP-0042')",
    )

    department: Mapped[AdminDepartment] = mapped_column(
        SAEnum(AdminDepartment, name="admin_department", native_enum=False),
        nullable=False,
        comment="Functional team this admin belongs to",
    )

    designation: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Job title displayed in the admin panel (e.g. 'Senior Support Agent')",
    )

    # ── Work Contact ──────────────────────────────────────────────────────────

    work_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
        comment=(
            "Work email address. Separate from the personal email on the User record. "
            "Used for internal communications and audit notifications."
        ),
    )

    work_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Work phone number in E.164 format (e.g. '+919876543210')",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    admin_status: Mapped[AdminStatus] = mapped_column(
        SAEnum(AdminStatus, name="admin_status", native_enum=False),
        nullable=False,
        default=AdminStatus.INACTIVE,
        comment="Operational status of this admin account",
    )

    # ── Security ──────────────────────────────────────────────────────────────

    mfa_enforced: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True requires MFA on every login. Default True for all admins. "
            "Setting to False requires explicit security policy approval."
        ),
    )

    ip_whitelist: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        comment=(
            "Allowed IP addresses or CIDR ranges for this admin. "
            "NULL disables IP-based access restrictions. "
            "Format: ['203.0.113.1', '10.0.0.0/8']"
        ),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent successful admin login",
    )

    last_login_ip: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="IP address of the most recent successful login (for audit trail)",
    )

    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Consecutive failed login attempts. Reset to 0 on successful login.",
    )

    account_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Timestamp until which this admin account is locked due to failed logins. "
            "NULL = not locked. Checked by the auth service on every login attempt."
        ),
    )

    # ── Feature Access Flags ──────────────────────────────────────────────────

    can_impersonate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True allows this admin to view the platform as a specific customer or "
            "vendor for debugging. Every impersonation session is AuditLogged."
        ),
    )

    can_access_financials: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True grants access to full payment amounts, bank account details, "
            "and settlement records. Typically granted only to Finance department."
        ),
    )

    can_export_data: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True allows bulk data export from the admin panel. "
            "Subject to approval workflow; all exports are AuditLogged."
        ),
    )

    # ── Employment ────────────────────────────────────────────────────────────

    joined_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date this admin joined the Tyohaar team",
    )

    reporting_to_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "FK to the admin's direct manager. "
            "SET NULL when manager is deactivated — preserves the direct report's account."
        ),
    )

    # ── Activity ──────────────────────────────────────────────────────────────

    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last admin panel action (updated on every API call)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship(
        "User",
        lazy="noload",
    )

    role: Mapped[AdminRole] = relationship(
        "AdminRole",
        back_populates="admins",
        lazy="noload",
    )

    reporting_to: Mapped[Admin | None] = relationship(
        "Admin",
        foreign_keys="[Admin.reporting_to_id]",
        remote_side="[Admin.id]",
        back_populates="reports",
        lazy="noload",
    )

    reports: Mapped[list[Admin]] = relationship(
        "Admin",
        foreign_keys="[Admin.reporting_to_id]",
        back_populates="reporting_to",
        lazy="noload",
        cascade="save-update, merge",
    )

    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="actor",
        lazy="noload",
        cascade="save-update, merge",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """True when the account is temporarily locked due to failed login attempts."""
        if self.account_locked_until is None:
            return False
        from datetime import datetime, timezone
        return datetime.now(tz=timezone.utc) < self.account_locked_until

    @property
    def is_active(self) -> bool:
        """True when admin_status is ACTIVE."""
        return self.admin_status == AdminStatus.ACTIVE

    @property
    def can_login(self) -> bool:
        """True when the admin may authenticate to the panel."""
        return self.admin_status == AdminStatus.ACTIVE and not self.is_locked

    @property
    def is_super_admin(self) -> bool:
        """
        True when the assigned role grants super admin privileges.

        Requires the `role` relationship to be loaded.
        Use `selectin` or `joined` loading strategy when checking this property.
        """
        return bool(self.role and self.role.is_super_admin)

    def __repr__(self) -> str:
        return (
            f"<Admin id={self.id} user_id={self.user_id} "
            f"department={self.department} status={self.admin_status}>"
        )
