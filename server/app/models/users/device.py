"""
UserDevice — registered devices for a user account.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import DeviceType, Platform
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class UserDevice(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Represents a physical device registered to a user account.

    One user can have many devices. This table is the canonical source of
    truth for push notification token management and trusted-device status.

    The composite unique constraint on (user_id, device_id) allows the same
    physical device to appear in different user records (family sharing), while
    preventing duplicate registrations for the same user+device pair.

    push_notification_token should be synced from UserSession on every app open,
    as FCM/APNs tokens can rotate silently without app reinstall.
    """

    __tablename__ = "user_devices"

    __table_args__ = (
        # A device_id appears once per user, but can appear across users
        UniqueConstraint("user_id", "device_id", name="uq_user_devices_user_device"),
        Index("ix_user_devices_user_id", "user_id"),
        Index("ix_user_devices_push_token", "push_notification_token"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Device Identity ───────────────────────────────────────────────────────

    device_id: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment=(
            "Stable hardware/OS-level identifier. "
            "Android: android_id. iOS: identifierForVendor. "
            "Web: browser-generated persistent UUID stored in localStorage."
        ),
    )

    device_type: Mapped[DeviceType] = mapped_column(
        SAEnum(DeviceType, name="device_type", native_enum=False),
        nullable=False,
        default=DeviceType.MOBILE,
    )

    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform", native_enum=False),
        nullable=False,
    )

    # ── Hardware Details ──────────────────────────────────────────────────────

    manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Device manufacturer (e.g., 'Apple', 'Samsung', 'OnePlus')",
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Device model name (e.g., 'iPhone 15 Pro', 'Galaxy S24')",
    )

    # ── Software Details ──────────────────────────────────────────────────────

    os: Mapped[str | None] = mapped_column(String(50), nullable=True)

    os_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Full OS version string (e.g., '17.2.1', '14')",
    )

    app_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Tyohaar app version last seen on this device",
    )

    # ── Push Notifications ────────────────────────────────────────────────────

    push_notification_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "FCM registration token (Android/Web) or APNs device token (iOS). "
            "Refreshed on every app foreground event and synced from UserSession."
        ),
    )

    # ── Locale ────────────────────────────────────────────────────────────────

    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="IANA timezone last reported by this device",
    )

    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="BCP-47 language tag last reported by this device",
    )

    # ── Activity ──────────────────────────────────────────────────────────────

    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last API call from this device",
    )

    # ── Security Flags ────────────────────────────────────────────────────────

    is_trusted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "Trusted devices bypass additional verification challenges. "
            "Set after successful MFA confirmation on this device."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_rooted: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment=(
            "Indicates if the device has been rooted (Android) or jailbroken (iOS). "
            "Null = unknown. True = high-risk device; apply stricter auth policies."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return (
            f"<UserDevice id={self.id} user_id={self.user_id} "
            f"platform={self.platform} model={self.model!r}>"
        )
