from __future__ import annotations

from datetime import date
from decimal import Decimal


def calculate_package_total(items: list[dict]) -> Decimal:
    """Sum base_price * quantity for each item dict."""
    total = Decimal("0.00")
    for item in items:
        price = Decimal(str(item.get("base_price", "0")))
        quantity = int(item.get("quantity", 1))
        total += price * quantity
    return total


def validate_price_range(price: Decimal) -> bool:
    """Return True if price falls within the allowed min/max bounds."""
    from app.services.packages.constants import MAX_PACKAGE_PRICE, MIN_PACKAGE_PRICE
    return MIN_PACKAGE_PRICE <= price <= MAX_PACKAGE_PRICE


def is_package_available_on_date(
    availability_slots: list,
    target_date: date,
) -> bool:
    """
    Return True if the package has an available slot on target_date.

    `availability_slots` is a list of PackageAvailability ORM instances or
    dicts with at minimum `available_date`, `is_available`, and `slots_available`.
    """
    for slot in availability_slots:
        if hasattr(slot, "available_date"):
            slot_date = slot.available_date
            is_avail = slot.is_available
            slots = slot.slots_available
        else:
            slot_date = slot.get("available_date")
            is_avail = slot.get("is_available", True)
            slots = slot.get("slots_available", 0)

        if slot_date == target_date:
            return bool(is_avail and slots > 0)

    return False
