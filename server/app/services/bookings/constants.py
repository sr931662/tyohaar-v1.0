from __future__ import annotations

from decimal import Decimal

BOOKING_CUTOFF_HOURS = 24
CANCELLATION_WINDOW_HOURS = 48
RESCHEDULE_WINDOW_HOURS = 48
MAX_BOOKING_ITEMS = 10
CANCELLATION_FEE_PERCENTAGE = Decimal("0.10")

VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "refunded": set(),
    "disputed": {"confirmed", "cancelled"},
    "no_show": set(),
    "rescheduled": {"confirmed", "cancelled"},
}

# Longest free-text customisation accepted on a booking line — the characters
# a customer wants on a marquee letter set, for example. Bounded because the
# value goes into BookingItem.notes and, unlike a `choices` pick, there is no
# list to validate it against.
MAX_CUSTOMIZATION_LENGTH = 100

# A line with no `choices` takes a number, not free text: the characters are
# stocked digits a vendor physically brings, one per digit. The count of them
# is the line's quantity, so this is both the digit cap and the quantity cap
# for such a line — kept in step with _maxCustomizationDigits in the app.
MAX_CUSTOMIZATION_DIGITS = 4
