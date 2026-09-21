"""
Payments domain constants.
"""

from __future__ import annotations

from decimal import Decimal

MIN_PAYMENT_AMOUNT = Decimal("1.00")
MAX_PAYMENT_AMOUNT = Decimal("1000000.00")
MAX_REFUND_PERCENTAGE = Decimal("1.00")          # 100%
PAYMENT_EXPIRY_SECONDS = 900                      # 15 min payment window
MAX_RETRY_ATTEMPTS = 3
PLATFORM_FEE_PERCENTAGE = Decimal("0.02")        # 2% platform fee
GST_ON_PLATFORM_FEE = Decimal("0.18")            # 18% GST on platform fee

SUPPORTED_GATEWAYS = {"razorpay", "stripe", "cashfree", "phonepe", "paytm", "offline"}

# ── Razorpay webhook events ───────────────────────────────────────────────────
# Only these move a payment out of PENDING. Every other event Razorpay can
# deliver (payment.authorized, payment.pending, payment.dispute.*, and any
# event added to the dashboard subscription later) is stored for audit and
# left to the two below, so an unexpected subscription cannot transition a
# payment by accident.
#
# order.paid is included as a success event because it is emitted once an
# order is fully paid; it arrives alongside payment.captured and the
# idempotency guard makes whichever lands second a no-op.
WEBHOOK_SUCCESS_EVENTS = frozenset({"payment.captured", "order.paid"})
WEBHOOK_FAILURE_EVENTS = frozenset({"payment.failed"})

# Coupon discount types
COUPON_TYPE_PERCENTAGE = "percentage"
COUPON_TYPE_FLAT = "flat"
MAX_COUPON_DISCOUNT_PERCENTAGE = Decimal("0.50")  # max 50% off
