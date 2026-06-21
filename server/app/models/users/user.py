"""
User — master identity record for every participant on the Tyohaar platform.

Supersedes the legacy app/models/user.py (which uses db/base.py).
All new code must import User from this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    AccountStatus,
    LoginMethod,
    UserRole,
    UserType,
    VerificationStatus,
)
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.address import UserAddress
    from app.models.users.device import UserDevice
    from app.models.users.profile import UserProfile


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Central identity record for all platform participants.

    Separation of concerns:
    - Authentication and security fields live here.
    - Personal/demographic data lives in UserProfile (1:1 via profile relation).
    - Saved addresses live in UserAddress (1:N).
    - Device registrations live in UserDevice (1:N).
    - Financial data lives in separate Wallet/Membership models.

    Phone is the primary identifier; email is optional but unique when present.
    `full_name` is a denormalized display convenience — when set, it overrides
    first_name + last_name for display purposes (supports single-name individuals).
    """

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_role_status", "role", "account_status"),
        Index("ix_users_last_login_at", "last_login_at"),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count_non_negative"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    phone: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        comment="E.164-formatted phone number (+919876543210). Primary login identifier.",
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="RFC 5321 email. Optional for customers; required for admin/vendor accounts.",
    )

    username: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional unique handle. Alphanumeric + underscore only.",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment=(
            "Denormalized display name. Preferred over first+last when present. "
            "Useful for single-name individuals or imported contacts."
        ),
    )

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Authorization ─────────────────────────────────────────────────────────

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.CUSTOMER,
        index=True,
    )

    user_type: Mapped[UserType] = mapped_column(
        SAEnum(UserType, name="user_type", native_enum=False),
        nullable=False,
        default=UserType.INDIVIDUAL,
    )

    # ── Account Lifecycle ─────────────────────────────────────────────────────

    account_status: Mapped[AccountStatus] = mapped_column(
        SAEnum(AccountStatus, name="account_status", native_enum=False),
        nullable=False,
        default=AccountStatus.PENDING_VERIFICATION,
        index=True,
    )

    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status", native_enum=False),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
    )

    # ── Authentication ────────────────────────────────────────────────────────

    primary_login_provider: Mapped[LoginMethod] = mapped_column(
        SAEnum(LoginMethod, name="login_method", native_enum=False),
        nullable=False,
        default=LoginMethod.OTP_PHONE,
        comment="The auth method this user registered with",
    )

    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Updated on every successful authentication event",
    )

    # ── Security ──────────────────────────────────────────────────────────────

    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Consecutive failed attempts since last successful login. Reset on success.",
    )

    account_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "When set, all login attempts are rejected until this timestamp. "
            "Applied by the auth layer after N consecutive failures."
        ),
    )

    password_last_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Relevant only for accounts using password-based authentication",
    )

    last_password_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Future-ready flag for TOTP / hardware key MFA support",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    profile: Mapped[UserProfile] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )

    addresses: Mapped[list[UserAddress]] = relationship(
        "UserAddress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    devices: Mapped[list[UserDevice]] = relationship(
        "UserDevice",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    # ── Computed Properties ───────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.phone

    @property
    def is_locked(self) -> bool:
        from datetime import timezone
        return (
            self.account_locked_until is not None
            and datetime.now(timezone.utc) < self.account_locked_until
        )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone!r} role={self.role}>"
