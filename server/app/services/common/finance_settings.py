"""
Platform finance settings, stored in ``app_settings`` and edited only from the
admin portal (Settings → Finance).

GST is off until an admin switches it on. A missing, inactive or unparsable row
all read as "off", so a database that has not had the seed migration yet
behaves like a fresh install rather than charging tax by accident.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.models.common.app_setting import AppSetting
from app.models.enums import AppSettingDataType

GST_ENABLED_KEY = "finance.gst_enabled"
FINANCE_GROUP = "finance"

# The rate is fixed; the admin switch only decides whether it is charged.
GST_RATE = Decimal("0.18")
GST_RATE_PERCENT = 18

_TRUE = {"true", "1", "yes", "on"}


def parse_bool(raw: str | None) -> bool:
    return str(raw).strip().lower() in _TRUE if raw is not None else False


async def read_gst_enabled(uow) -> bool:
    """Whether new bookings should be charged GST. Defaults to False."""
    setting = await uow.common.settings.get_by_key(GST_ENABLED_KEY)
    if setting is None or not setting.is_active:
        return False
    return parse_bool(setting.value if setting.value is not None else setting.default_value)


async def write_gst_enabled(uow, enabled: bool, admin_id: UUID) -> AppSetting:
    value = "true" if enabled else "false"
    existing = await uow.common.settings.get_by_key(GST_ENABLED_KEY)
    if existing is not None:
        return await uow.common.settings.update(
            existing, {"value": value, "is_active": True, "updated_by_id": admin_id}
        )
    return await uow.common.settings.create({
        "key": GST_ENABLED_KEY,
        "group": FINANCE_GROUP,
        "label": "Charge GST on bookings",
        "description": (
            "When on, 18% GST is added to new bookings on the post-discount amount. "
            "When off, no tax is charged or shown. Existing bookings keep their amounts."
        ),
        "value": value,
        "default_value": "false",
        "data_type": AppSettingDataType.BOOLEAN,
        "is_sensitive": False,
        "is_readonly": False,
        "created_by_id": admin_id,
        "updated_by_id": admin_id,
    })
