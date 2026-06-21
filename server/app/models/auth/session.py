"""
UserSession — multi-device session management for authenticated users.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import (
    DeviceType,
    LoginMethod,
    Platform,
    SessionStatus,
    TokenRevocationReason,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Represents a single authenticated session on a specific device.

    Session architecture:
    - One session is created per login event per device.
    - A user may have many concurrent sessions (phone + tablet + web browser).
    - Every authenticated API request must validate:
        1. session.is_active is True
        2. session.is_revoked is False
        3. session.status == ACTIVE
        4. datetime.utcnow() < session.expires_at
        5. The request's access_jti matches session.access_jti (server-side
           access token invalidation without waiting for JWT expiry).
    - session_token is an opaque random value (not a JWT). It identifies this
      session record in the database and is stored securely on the client.
    - access_jti is updated every time a new access token is issued for this
      session, enabling immediate invalidation of the previous access token.
    - push_notification_token must be refreshed on every app open because
      FCM/APNs tokens can rotate without warning.

    Security events that should trigger revocation:
    - Password change
    - Suspicious IP/location change
    - Admin action
    - Refresh token reuse detected (entire token family + session revoked)
    """

    __tablename__ = "user_sessions"

    __table_args__ = (
        Index("ix_user_session_user_id_active", "user_id", "is_active"),
        Index("ix_user_session_session_token", "session_token", unique=True),
        Index("ix_user_session_device_id", "device_id"),
        Index("ix_user_session_expires_at", "expires_at"),
        Index("ix_user_session_status", "status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Session Identity ──────────────────────────────────────────────────────

    session_token: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment=(
            "Cryptographically random opaque token (not a JWT). "
            "Stored in the client's secure storage and sent as a header. "
            "Used to look up this session record efficiently."
        ),
    )

    access_jti: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment=(
            "JWT ID (jti claim) of the most recently issued access token for this session. "
            "Auth middleware rejects access tokens whose jti does not match this value, "
            "enabling server-side access token invalidation before natural expiry."
        ),
    )

    # ── Device ────────────────────────────────────────────────────────────────

    device_id: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment=(
            "Stable hardware/OS-level device identifier. "
            "Android: android_id. iOS: identifierForVendor. "
            "Used to detect session hijacking across different devices."
        ),
    )

    device_name: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="User-visible device name (e.g., 'Priya's iPhone 15 Pro')",
    )

    device_type: Mapped[DeviceType | None] = mapped_column(
        SAEnum(DeviceType, name="device_type", native_enum=False),
        nullable=True,
    )

    platform: Mapped[Platform | None] = mapped_column(
        SAEnum(Platform, name="platform", native_enum=False),
        nullable=True,
    )

    os: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Operating system name (e.g., 'iOS', 'Android', 'Windows')",
    )

    os_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Full OS version string (e.g., '17.2.1', '14')",
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Browser name for web sessions (e.g., 'Chrome', 'Safari'). Null for native apps.",
    )

    browser_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    app_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Tyohaar app semantic version (e.g., '2.4.1')",
    )

    # ── Network & Geolocation ─────────────────────────────────────────────────

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address at login time (supports IPv4 and IPv6)",
    )

    country_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        comment="ISO 3166-1 alpha-2 country code resolved from login IP (e.g., 'IN')",
    )

    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="State or administrative region resolved from login IP",
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="City resolved from login IP geolocation",
    )

    # ── Client Preferences ────────────────────────────────────────────────────

    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="IANA timezone string reported by the client (e.g., 'Asia/Kolkata')",
    )

    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="BCP-47 language tag reported by the client (e.g., 'hi', 'en')",
    )

    # ── Authentication Context ────────────────────────────────────────────────

    login_method: Mapped[LoginMethod] = mapped_column(
        SAEnum(LoginMethod, name="login_method", native_enum=False),
        nullable=False,
        comment="Which authentication method was used to create this session",
    )

    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status", native_enum=False),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )

    # ── Activity Timestamps ───────────────────────────────────────────────────

    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when this session was first created",
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment=(
            "Updated on every authenticated API request. "
            "Used to enforce idle-session timeouts and detect abandoned sessions."
        ),
    )

    logout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when the user explicitly logs out",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment=(
            "Absolute session ceiling. After this, the user must re-authenticate "
            "regardless of recent activity. Controlled by remember_me setting."
        ),
    )

    # ── Session Flags ─────────────────────────────────────────────────────────

    remember_me: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="If True, a long-lived TTL is applied (e.g., 30 days instead of 24 hours)",
    )

    is_trusted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "Trusted devices skip step-up authentication challenges. "
            "Set after a successful MFA confirmation on this device."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revocation_reason: Mapped[TokenRevocationReason | None] = mapped_column(
        SAEnum(TokenRevocationReason, name="token_revocation_reason", native_enum=False),
        nullable=True,
    )

    # ── Push Notifications ────────────────────────────────────────────────────

    push_notification_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "FCM (Android/Web) or APNs (iOS) device token for push delivery. "
            "Must be refreshed on every app foreground event; tokens rotate silently."
        ),
    )

    # ── Audit ─────────────────────────────────────────────────────────────────

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full User-Agent string for bot detection and device classification",
    )

    # ── Computed Properties ───────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        """True only if this session can be used to authenticate a request."""
        return (
            self.is_active
            and not self.is_revoked
            and self.status == SessionStatus.ACTIVE
            and datetime.now(timezone.utc) < self.expires_at
        )

    def __repr__(self) -> str:
        return (
            f"<UserSession id={self.id} user_id={self.user_id} "
            f"platform={self.platform} status={self.status}>"
        )
