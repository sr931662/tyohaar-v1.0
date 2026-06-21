"""Common service helper utilities."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def slugify(text: str) -> str:
    """
    Convert *text* to a URL-safe slug:
    lowercase, spaces become hyphens, non-alphanumeric-hyphen characters removed.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def sort_faqs_by_category(faqs: list[Any]) -> dict[str, list[Any]]:
    """
    Group a list of FAQ objects (or dicts) by their faq_category value.
    Returns a dict mapping category name → ordered list of FAQs.
    """
    grouped: dict[str, list[Any]] = {}
    for faq in faqs:
        category = (
            faq.faq_category
            if hasattr(faq, "faq_category")
            else faq.get("faq_category", "other")
        )
        category_key = str(category)
        grouped.setdefault(category_key, []).append(faq)
    return grouped


def is_banner_active(banner: dict[str, Any], now: datetime) -> bool:
    """
    Return True when the banner dict satisfies all activity conditions:
    - is_active is True
    - display_start_at is None OR <= now
    - display_end_at is None OR >= now
    """
    if not banner.get("is_active", False):
        return False
    display_start = banner.get("display_start_at")
    display_end = banner.get("display_end_at")
    if display_start is not None and now < display_start:
        return False
    if display_end is not None and now > display_end:
        return False
    return True


def parse_setting_value(value: str, value_type: str) -> Any:
    """
    Deserialise *value* (stored as TEXT) using the *value_type* hint.

    Supported value_type values:
        "string"  → str
        "integer" → int
        "float"   → float
        "boolean" → bool  (true/1/yes → True, all else False)
        "json"    → parsed JSON
        "list"    → parsed JSON array
    """
    vt = value_type.lower().strip()
    if vt == "string":
        return value
    if vt == "integer":
        return int(value)
    if vt == "float":
        return float(value)
    if vt == "boolean":
        return value.strip().lower() in ("true", "1", "yes")
    if vt in ("json", "list"):
        return json.loads(value)
    # Fallback — return raw string
    return value
