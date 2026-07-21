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

from app.models.enums import CouponType
from app.services.payments.constants import (
    COUPON_TYPE_PERCENTAGE,
    GST_ON_PLATFORM_FEE,
    MAX_COUPON_DISCOUNT_PERCENTAGE,
    PAYMENT_EXPIRY_SECONDS,
)


def calculate_platform_fee(amount: Decimal) -> Decimal:
    """
    Platform fee has been removed project-wide — customers are charged only
    the package price (+ any product GST), never a separate Tyohaar fee.
    Kept as a function (rather than deleted) since callers still pass its
    result into the total/GST-on-fee formula; it now always returns 0.
    """
    return Decimal("0.00")


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


def calculate_discount_amount(
    amount: Decimal,
    coupon_type: CouponType,
    discount_value: Decimal,
    max_discount: Decimal | None,
    *,
    package_base_price: Decimal | None = None,
) -> Decimal:
    """
    DiscountEngine's calculation entrypoint — branches on the actual
    CouponType enum (unlike the older calculate_coupon_discount, which only
    ever distinguishes 'percentage' vs. everything-else-as-flat). Supports
    PERCENTAGE, FIXED_AMOUNT, FIXED_PRICE, FREE_SERVICE. CASHBACK is granted
    post-completion (not deducted at checkout), so it returns 0 here.

    Raises ValueError for the reserved-not-yet-implemented types
    (BUY_X_GET_Y, FREE_ADDON) — callers should never reach here for those,
    since CouponCreate/CouponUpdate already reject creating/activating them.
    """
    if coupon_type == CouponType.PERCENTAGE:
        raw_discount = (amount * discount_value / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        if max_discount is not None:
            raw_discount = min(raw_discount, max_discount)
        safety_cap = (amount * MAX_COUPON_DISCOUNT_PERCENTAGE).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
        raw_discount = min(raw_discount, safety_cap)
    elif coupon_type == CouponType.FIXED_AMOUNT:
        raw_discount = discount_value.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    elif coupon_type == CouponType.FIXED_PRICE:
        base = package_base_price if package_base_price is not None else amount
        raw_discount = max(Decimal("0.00"), base - discount_value)
    elif coupon_type == CouponType.FREE_SERVICE:
        raw_discount = amount
    elif coupon_type == CouponType.CASHBACK:
        return Decimal("0.00")
    else:
        raise ValueError(f"coupon_type '{coupon_type}' is not yet supported by the discount engine.")

    return max(Decimal("0.00"), min(raw_discount, amount))


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
    Any other gateway value fails closed (returns False) — no other gateway
    integration exists yet, so there is no verification scheme to check
    against; silently trusting an unverified payload would let anyone hit
    the webhook/verify endpoints with an arbitrary {gateway} path value to
    bypass signature checking entirely.
    """
    if gateway.lower() == "razorpay":
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    return False


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
