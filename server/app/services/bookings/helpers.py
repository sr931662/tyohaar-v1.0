from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


def calculate_booking_total(items: list[dict]) -> Decimal:
    """Sum final_price for each item dict."""
    total = Decimal("0.00")
    for item in items:
        total += Decimal(str(item.get("final_price", "0")))
    return total


def calculate_cancellation_fee(total: Decimal, percentage: Decimal) -> Decimal:
    """Return fee = total * percentage, rounded to 2dp."""
    return (total * percentage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_refund_amount(total: Decimal, fee: Decimal) -> Decimal:
    """Return refund = total - fee (floored at zero)."""
    refund = total - fee
    return max(Decimal("0.00"), refund)


def is_booking_cancellable(event_date: datetime, cutoff_hours: int) -> bool:
    """Return True if now is at least cutoff_hours before event_date."""
    from datetime import timedelta
    now = datetime.now(tz=timezone.utc)
    # Ensure event_date is offset-aware
    if event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    return now <= event_date - timedelta(hours=cutoff_hours)


def is_booking_reschedule_eligible(event_date: datetime, cutoff_hours: int) -> bool:
    """Return True if now is at least cutoff_hours before event_date."""
    return is_booking_cancellable(event_date, cutoff_hours)


def validate_status_transition(current: str, next_status: str) -> bool:
    """Return True if the transition from current → next_status is valid."""
    from app.services.bookings.constants import VALID_STATUS_TRANSITIONS
    allowed = VALID_STATUS_TRANSITIONS.get(current.lower(), set())
    return next_status.lower() in allowed


def generate_booking_reference() -> str:
    """Return 'TYO' + 8 random uppercase alphanumeric characters."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=8))
    return f"TYO{suffix}"


# ── Customisable lines ────────────────────────────────────────────────────────
#
# A customisable package line takes one of two shapes, decided by the line
# itself rather than by anything named here, so a vendor adding an add-on in
# the portal needs no code change:
#
#   * a fixed `choices` list — the customer picks one of the vendor's options;
#   * no `choices` — the line takes CHARACTERS from its `character_set`
#     (digits, letters or alphanumeric). The vendor stocks physical characters
#     (a marquee letter set, foil balloon letters), so "20" is a 2 and a 0 and
#     "ANITA 30" is seven characters: each billed at the line's base price.
#
# Both rules live here rather than inside create_booking so the booking path
# and its tests exercise the same code.


def is_numeric_line(line) -> bool:
    """True when a customisable line takes typed characters, not a choice.

    Name kept from when the only such line was a dialled number; it now means
    "takes characters from the line's character_set".
    """
    return bool(getattr(line, "is_customizable", False)) and not (
        getattr(line, "choices", None) or []
    )


# Allowed characters per character set. Letters are stored upper-case because
# physical letters (foil balloons, marquee letters) come in one case.
_DIGITS = "0123456789"
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ALLOWED = {
    "digits": _DIGITS,
    "letters": _LETTERS,
    "alphanumeric": _LETTERS + _DIGITS,
}


def line_character_set(line) -> str:
    """The line's character set as a plain string; unknown/missing means digits."""
    raw = getattr(line, "character_set", None)
    raw = getattr(raw, "value", raw)
    return raw if raw in _ALLOWED else "digits"


def character_cap(line, *, max_digits: int, max_chars: int) -> int:
    """
    The most characters this line can take: the platform cap for its character
    set, lowered by the vendor's own max_quantity. Applied when the value is
    stored, so the text on the booking and the quantity billed always agree.
    """
    cap = max_digits if line_character_set(line) == "digits" else max_chars
    vendor_cap = getattr(line, "max_quantity", None)
    if vendor_cap is not None and vendor_cap >= 1:
        cap = min(cap, vendor_cap)
    return cap


def normalize_characters(value: str, character_set: str) -> str:
    """
    Keep only what the character set allows (upper-casing letters). Spaces
    separate words in letters/alphanumeric lines — collapsed to single spaces
    and never leading/trailing — and are dropped entirely for digits.
    """
    allowed = _ALLOWED.get(character_set, _DIGITS)
    out: list[str] = []
    for ch in value.upper():
        if ch in allowed:
            out.append(ch)
        elif ch.isspace() and character_set != "digits" and out and out[-1] != " ":
            out.append(" ")
    return "".join(out).strip()


def billable_characters(value: str | None) -> int:
    """Characters that are billed: everything except spaces."""
    return len((value or "").replace(" ", ""))


def truncate_billable(value: str, cap: int) -> str:
    """Cut `value` after `cap` billable characters, keeping its spaces tidy."""
    out: list[str] = []
    count = 0
    for ch in value:
        if ch == " ":
            out.append(ch)
            continue
        if count >= cap:
            break
        out.append(ch)
        count += 1
    return "".join(out).strip()


def resolve_customization(
    line,
    supplied: dict,
    *,
    max_length: int,
    max_digits: int,
    max_chars: int = 20,
) -> str | None:
    """
    What the customer specified for one line, or None.

    A `choices` line must match one of the vendor's options, so a tampered
    client cannot order something never offered. A character line keeps only
    what its character_set allows — everything else is dropped rather than
    ordered — capped by character_cap, since every character is a physical
    item the vendor carries and a charge on the line.
    """
    value = supplied.get(str(line.id))
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    offered = getattr(line, "choices", None) or []
    if offered:
        # Still bounded: a choice comes from the vendor, and the column it
        # lands in is not unlimited.
        return value[:max_length] if value in offered else None

    if not getattr(line, "is_customizable", False):
        return None

    cleaned = normalize_characters(value, line_character_set(line))
    if not billable_characters(cleaned):
        return None
    return truncate_billable(cleaned, character_cap(line, max_digits=max_digits, max_chars=max_chars))


def digit_quantity(line, digits: str) -> int:
    """
    Characters ordered on a character line: one per non-space character.

    "20" is a 2 and a 0, so it bills at 2 x the line's base price, and
    "ANITA 30" is seven characters. Still capped by max_quantity — a vendor
    who owns three characters cannot supply four.
    """
    qty = billable_characters(digits)
    max_quantity = getattr(line, "max_quantity", None)
    if max_quantity is not None:
        qty = min(qty, max_quantity)
    return max(qty, 1)


# ── Booking totals ────────────────────────────────────────────────────────────

GST_RATE = Decimal("0.18")
_PAISE = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Round to paise, half-up — the rule the app mirrors when it previews a total."""
    return Decimal(value).quantize(_PAISE, rounding=ROUND_HALF_UP)


def compute_booking_amounts(
    subtotal: Decimal,
    discount: Decimal,
    *,
    platform_fee: Decimal = Decimal("0.00"),
    tax_rate: Decimal = GST_RATE,
) -> dict[str, Decimal]:
    """
    subtotal -> discount -> tax -> total, in one place.

    Tax is charged on the post-discount base (never negative), rounded half-up
    to paise. The discount is clamped to the subtotal so an oversized coupon
    can't produce a negative taxable amount and a negative total.
    """
    subtotal = money(subtotal)
    discount = min(max(money(discount), Decimal("0.00")), subtotal)
    taxable = subtotal - discount
    tax = money(taxable * tax_rate)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "taxable": taxable,
        "tax": tax,
        "total": taxable + tax + platform_fee,
    }
