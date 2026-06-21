"""
Wallets domain constants.
"""

from __future__ import annotations

from decimal import Decimal

MIN_WALLET_CREDIT = Decimal("1.00")
MAX_WALLET_CREDIT = Decimal("100000.00")      # per transaction
MAX_WALLET_BALANCE = Decimal("500000.00")
MIN_WALLET_DEBIT = Decimal("1.00")
REWARD_EXPIRY_DAYS = 365
CASHBACK_PERCENTAGE = Decimal("0.01")         # 1% default cashback
DEFAULT_REWARD_POINTS_CONVERSION = Decimal("1.00")  # 1 point = ₹1
