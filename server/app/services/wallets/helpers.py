"""
Wallets domain helpers — pure functions, no I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal

from app.services.wallets.constants import DEFAULT_REWARD_POINTS_CONVERSION


def validate_debit_amount(balance: Decimal, amount: Decimal) -> bool:
    """Return True if the wallet has sufficient available balance for the debit."""
    return balance >= amount


def calculate_cashback(amount: Decimal, percentage: Decimal) -> Decimal:
    """Return the cashback amount for a given transaction amount and percentage."""
    return (amount * percentage).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def calculate_reward_points_value(
    points: int,
    conversion_rate: Decimal = DEFAULT_REWARD_POINTS_CONVERSION,
) -> Decimal:
    """Convert loyalty points to a monetary Decimal value."""
    return (Decimal(points) * conversion_rate).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def is_reward_expired(expires_at: datetime | None) -> bool:
    """Return True if expires_at is set and has passed."""
    if expires_at is None:
        return False
    now = datetime.now(tz=timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now > expires_at


def format_wallet_balance(amount: Decimal) -> str:
    """Return a human-readable rupee balance string, e.g. '₹1,234.56'."""
    quantized = amount.quantize(Decimal("0.01"))
    # Format with thousand separators
    parts = f"{quantized:,.2f}".split(".")
    return f"₹{parts[0]}.{parts[1]}"
