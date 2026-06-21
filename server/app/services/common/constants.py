"""Common service constants."""

from __future__ import annotations

MAX_BANNERS_ACTIVE = 10
MAX_FAQ_ITEMS = 200
FAQ_CATEGORIES: list[str] = [
    "general",
    "booking",
    "payment",
    "vendor",
    "account",
    "other",
]
APP_SETTING_CACHE_TTL = 300  # 5 minutes — hint for router-layer caching
MAX_SETTING_VALUE_LENGTH = 5000
TERMS_CURRENT_VERSION = "v1.0"  # default version string for new terms
