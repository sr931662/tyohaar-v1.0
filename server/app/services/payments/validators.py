"""
Payments domain validators — stateful checks that require the UoW/DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.models.enums import CouponType
from app.models.payments.coupon import Coupon
from app.models.payments.payment import Payment
from app.repositories.unit_of_work import UnitOfWork
from app.services.payments.constants import (
    MAX_PAYMENT_AMOUNT,
    MIN_PAYMENT_AMOUNT,
    SUPPORTED_GATEWAYS,
)
from app.services.payments.exceptions import (
    CouponExhaustedError,
    CouponExpiredError,
    CouponMinOrderNotMetError,
    CouponNotFoundError,
    CouponUserLimitReachedError,
    PaymentNotFoundError,
    RefundExceedsPaymentError,
    UnsupportedGatewayError,
)
from app.services.exceptions import ValidationError


async def validate_payment_exists(payment_id: uuid.UUID, uow: UnitOfWork) -> Payment:
    """Fetch and return the Payment, raising PaymentNotFoundError if absent."""
    payment = await uow.payments.payments.get_by_id(payment_id)
    if payment is None:
        raise PaymentNotFoundError(str(payment_id))
    return payment


def validate_payment_amount(amount: Decimal) -> None:
    """Raise ValidationError if amount is outside the allowed range."""
    if amount < MIN_PAYMENT_AMOUNT:
        raise ValidationError(
            f"Payment amount must be at least ₹{MIN_PAYMENT_AMOUNT}.",
            field="amount",
        )
    if amount > MAX_PAYMENT_AMOUNT:
        raise ValidationError(
            f"Payment amount cannot exceed ₹{MAX_PAYMENT_AMOUNT}.",
            field="amount",
        )


async def validate_coupon_applicable(
    coupon: Coupon,
    user_id: uuid.UUID,
    booking_id: uuid.UUID,
    amount: Decimal,
    uow: UnitOfWork,
) -> None:
    """
    Validate all eligibility conditions for a coupon against the current order.

    Checks (all must pass):
    - Coupon is active
    - Not expired
    - Global usage limit not reached
    - Minimum order amount satisfied
    - Per-user usage limit not reached

    Raises the appropriate CouponError subclass on the first failure.
    """
    now = datetime.now(tz=timezone.utc)

    if not coupon.is_active:
        raise CouponExpiredError("Coupon is no longer active.")

    if coupon.valid_from > now:
        raise CouponExpiredError("Coupon is not yet valid.")

    if coupon.valid_until is not None and coupon.valid_until < now:
        raise CouponExpiredError("Coupon has expired.")

    if coupon.is_exhausted:
        raise CouponExhaustedError()

    if coupon.min_order_value is not None and amount < coupon.min_order_value:
        raise CouponMinOrderNotMetError(
            f"Minimum order amount of ₹{coupon.min_order_value} is required."
        )

    # Per-user usage limit check
    if coupon.per_user_limit is not None:
        redemption_count = await uow.payments.coupon_redemptions.count_for_user(
            coupon.id, user_id
        )
        if redemption_count >= coupon.per_user_limit:
            raise CouponUserLimitReachedError(
                f"You have already used coupon '{coupon.code}' the maximum "
                f"{coupon.per_user_limit} time(s) allowed."
            )


def validate_refund_amount(payment: Payment, refund_amount: Decimal) -> None:
    """Raise RefundExceedsPaymentError if the refund would exceed what was paid."""
    if refund_amount > payment.final_amount:
        raise RefundExceedsPaymentError(
            f"Refund amount ₹{refund_amount} exceeds payment amount ₹{payment.final_amount}."
        )
    if refund_amount <= Decimal("0"):
        raise ValidationError("Refund amount must be greater than zero.", field="amount")


def validate_gateway_supported(gateway: str) -> None:
    """Raise UnsupportedGatewayError if gateway is not in SUPPORTED_GATEWAYS."""
    if gateway.lower() not in SUPPORTED_GATEWAYS:
        raise UnsupportedGatewayError(gateway)
