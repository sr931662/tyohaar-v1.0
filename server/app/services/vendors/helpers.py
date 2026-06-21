"""
Vendors service — pure helper functions (no I/O, no side effects).
"""

from __future__ import annotations

import html
import re
from datetime import date, time

from app.services.vendors.constants import MAX_RATING, MIN_RATING


def calculate_average_rating(ratings: list) -> float:
    """Return the arithmetic mean of *ratings*, rounded to 2 decimal places.

    Returns 0.0 for an empty list.
    """
    if not ratings:
        return 0.0
    return round(float(sum(ratings)) / len(ratings), 2)


def is_vendor_available(
    availability_slots: list,
    event_date: date,
    start_time: time,
    end_time: time,
) -> bool:
    """Return True if the vendor has an open work-schedule slot that covers
    *event_date* / *start_time*–*end_time* and there are no blocked periods
    that overlap the same range.

    *availability_slots* is expected to be a list of ORM objects that expose:
        - For VendorWorkSchedule: ``day_of_week``, ``is_working``,
          ``open_time``, ``close_time``
        - For VendorBlockedPeriod: ``start_date``, ``end_date``

    Pass only one model type at a time; the caller is responsible for
    providing the correct list.
    """
    day_name = event_date.strftime("%A").lower()  # e.g. "monday"

    for slot in availability_slots:
        # Work-schedule check
        if hasattr(slot, "day_of_week") and hasattr(slot, "is_working"):
            if str(slot.day_of_week).lower() == day_name and slot.is_working:
                open_t = slot.open_time
                close_t = slot.close_time
                if open_t is None or close_t is None:
                    continue
                if open_t <= start_time and end_time <= close_t:
                    return True

        # Blocked-period check: if any block covers the event_date the
        # vendor is NOT available (caller should pass blocked periods
        # separately and treat True as "is blocked").
        if hasattr(slot, "start_date") and hasattr(slot, "end_date"):
            if slot.start_date <= event_date <= slot.end_date:
                return False

    return False


def format_vendor_display_name(vendor_name: str, city: str) -> str:
    """Return a display-friendly combined name, e.g. 'Celebrations Co. · Mumbai'."""
    vendor_name = vendor_name.strip()
    city = city.strip()
    if city:
        return f"{vendor_name} · {city}"
    return vendor_name


def sanitize_review_text(text: str) -> str:
    """Strip HTML tags and dangerous characters from user-supplied review text."""
    # Unescape HTML entities first, then strip any remaining tags
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    # Remove null bytes and non-printable control characters (except whitespace)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()
