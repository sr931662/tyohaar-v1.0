"""
Payments domain helpers — pure functions, no I/O.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import string
from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal

from app.services.payments.constants import (
    COUPON_TYPE_PERCENTAGE,
    GST_ON_PLATFORM_FEE,
    MAX_COUPON_DISCOUNT_PERCENTAGE,
    PAYMENT_EXPIRY_SECONDS,
    PLATFORM_FEE_PERCENTAGE,
)


def calculate_platform_fee(amount: Decimal) -> Decimal:
    """Return the 2% Tyohaar platform fee for the given base amount."""
    return (amount * PLATFORM_FEE_PERCENTAGE).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def calculate_gst(platform_fee: Decimal) -> Decimal:
    """Return 18% GST applied to the platform fee."""
    return (platform_fee * GST_ON_PLATFORM_FEE).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def calculate_total_with_fees(base_amount: Decimal) -> Decimal:
    """Return base_amount + platform_fee + GST on platform_fee."""
    fee = calculate_platform_fee(base_amount)
    gst = calculate_gst(fee)
    return base_amount + fee + gst


def calculate_coupon_discount(
    amount: Decimal,
    coupon_type: str,
    discount_value: Decimal,
    max_discount: Decimal | None,
) -> Decimal:
    """
    Calculate the monetary discount for a given coupon.

    For COUPON_TYPE_PERCENTAGE: discount_value is treated as a percentage (0–100).
    For flat: discount_value is a direct monetary deduction.
    Result is capped at amount and, for percentage, also at MAX_COUPON_DISCOUNT_PERCENTAGE
    of the order amount if no explicit max_discount is supplied.
    """
    if coupon_type == COUPON_TYPE_PERCENTAGE:
        # discount_value is stored as percentage 0–100 in the DB
        raw_discount = (amount * discount_value / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        if max_discount is not None:
            raw_discount = min(raw_discount, max_discount)
        # Safety cap: never exceed MAX_COUPON_DISCOUNT_PERCENTAGE of order
        safety_cap = (amount * MAX_COUPON_DISCOUNT_PERCENTAGE).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        raw_discount = min(raw_discount, safety_cap)
    else:
        # Flat discount
        raw_discount = discount_value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # Never exceed the order amount
    return min(raw_discount, amount)


def apply_membership_discount(subtotal: Decimal, discount_percentage: Decimal) -> Decimal:
    """Return the monetary discount from an active membership's discount_percentage (0-100)."""
    return (subtotal * discount_percentage / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    gateway: str,
) -> bool:
    """
    Verify the HMAC-SHA256 webhook signature from a payment gateway.

    Razorpay: HMAC-SHA256(payload, secret) == signature (hex digest).
    Other gateways: stub — always returns True until implemented.
    """
    if gateway.lower() == "razorpay":
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    # Stubs for other gateways — implement per gateway SDK spec
    return True


def generate_payment_reference() -> str:
    """Return a unique payment reference: 'PAY' + 12 random alphanumeric characters."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=12))
    return f"PAY{suffix}"


def mask_card_number(card_number: str) -> str:
    """Return a masked card string showing only the last four digits: '****1234'."""
    cleaned = card_number.replace(" ", "").replace("-", "")
    return f"****{cleaned[-4:]}" if len(cleaned) >= 4 else "****"


def is_payment_expired(created_at: datetime, expiry_seconds: int = PAYMENT_EXPIRY_SECONDS) -> bool:
    """Return True if more than expiry_seconds have elapsed since created_at."""
    now = datetime.now(tz=timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).total_seconds() > expiry_seconds
