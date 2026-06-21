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

# Coupon discount types
COUPON_TYPE_PERCENTAGE = "percentage"
COUPON_TYPE_FLAT = "flat"
MAX_COUPON_DISCOUNT_PERCENTAGE = Decimal("0.50")  # max 50% off
