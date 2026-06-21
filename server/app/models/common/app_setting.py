"""
AppSetting — runtime-configurable key-value store for platform settings.

Provides a single source of truth for all platform constants that would
otherwise be hardcoded in application code.  Settings are read at runtime
and cached in-process (TTL configured separately in Redis).

Examples of settings managed here:
    platform_fee_pct          → 10           (INTEGER, payments group)
    max_coupon_discount_pct   → 30           (INTEGER, payments group)
    maintenance_mode          → false        (BOOLEAN, platform group)
    referral_bonus_amount     → 200.00       (FLOAT, rewards group)
    supported_cities          → ["MH", "DL"] (LIST, platform group)
    smtp_from_name            → "Tyohaar"    (STRING, notifications group)
    tax_rate_pct              → 18.0         (FLOAT, payments group)

Design principles:
1. All values are stored as TEXT and deserialised by the settings service
   using `data_type` to convert to the correct Python type.
2. `is_sensitive` masks the value in admin panel listings, logs, and error
   messages.  Examples: API keys, webhook secrets, encryption salts.
3. `is_readonly` flags settings that can ONLY be changed via DB migration
   or seed scripts (not via the admin panel UI), to prevent accidental
   runtime changes to critical constants.
4. `is_environment_specific` marks settings that intentionally differ
   across dev / staging / production environments.
5. `group` enables the admin panel to render settings in logical sections.
6. `default_value` is the fallback used by the settings service when `value`
   is NULL or the key does not exist.  Never change default_value in place —
   add a migration instead.

`key` naming convention: `snake_case_group_underscore_name`
    e.g. payments_platform_fee_pct, notifications_sms_sender_id
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import AppSettingDataType
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """
    A single runtime-configurable platform setting.

    The settings service reads settings with:
        SELECT value, data_type, default_value FROM app_settings
        WHERE key = :key AND is_active = true;

    And deserialises `value` (or `default_value` if value is NULL) based on
    `data_type`:
        STRING  → str(value)
        INTEGER → int(value)
        FLOAT   → float(value)
        BOOLEAN → value.lower() in ('true', '1', 'yes')
        JSON    → json.loads(value)
        LIST    → json.loads(value)  (expected to be a JSON array)

    Mutation is restricted:
    - `is_readonly = True`: setting must not be mutated via admin UI.
    - `is_sensitive = True`: value is masked in UI and logs.
    - Only super_admin role may mutate settings marked `is_environment_specific`.

    `updated_by_id` (from AuditMixin) captures which admin changed the value.
    Every value change must also produce an AuditLog entry.
    """

    __tablename__ = "app_settings"

    __table_args__ = (
        UniqueConstraint("key", name="uq_app_settings_key"),
        Index("ix_app_settings_group", "group"),
        Index("ix_app_settings_is_active", "is_active"),
        Index("ix_app_settings_is_sensitive", "is_sensitive"),
        Index("ix_app_settings_group_active", "group", "is_active"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment=(
            "Unique setting identifier in snake_case. "
            "Convention: {group}_{name} (e.g. 'payments_platform_fee_pct')"
        ),
    )

    group: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Logical grouping for admin panel sections "
            "(e.g. 'payments', 'notifications', 'platform', 'rewards')"
        ),
    )

    label: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Human-readable name displayed in the admin settings panel",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Explanation of what this setting controls, its valid range, "
            "and the impact of changing it. Required for all non-obvious settings."
        ),
    )

    # ── Value ─────────────────────────────────────────────────────────────────

    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Current setting value stored as TEXT. "
            "Deserialized using data_type. NULL falls back to default_value."
        ),
    )

    default_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Fallback value used when value is NULL. "
            "Treat as immutable; change default_value only via migration."
        ),
    )

    data_type: Mapped[AppSettingDataType] = mapped_column(
        SAEnum(AppSettingDataType, name="app_setting_data_type", native_enum=False),
        nullable=False,
        default=AppSettingDataType.STRING,
        comment="Python type to cast the stored TEXT value to at runtime",
    )

    # ── Access Control ────────────────────────────────────────────────────────

    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True masks the value in admin panel listings, log output, and error messages. "
            "Use for API keys, secrets, and PII-adjacent settings."
        ),
    )

    is_readonly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True prevents mutation via the admin UI. "
            "Only changeable via DB migration or seeding scripts."
        ),
    )

    is_environment_specific: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when this setting intentionally has different values across "
            "dev / staging / production. Flags for ops team awareness."
        ),
    )

    # ── Visibility ────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False disables the setting; settings service uses default_value instead",
    )

    def __repr__(self) -> str:
        display_value = "***" if self.is_sensitive else repr(self.value)
        return (
            f"<AppSetting key={self.key!r} group={self.group!r} "
            f"type={self.data_type} value={display_value}>"
        )
