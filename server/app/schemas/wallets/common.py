"""
Wallet domain — shared types, enums re-exports, and nested schemas.

Import from here instead of importing enums or sub-schemas individually.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.models.enums import Currency, RewardType, WalletTransactionType, WalletType
from app.models.wallets.wallet import WalletStatus  # local enum defined in wallet.py
from app.schemas.base import BaseSchema, MoneyAmount

# ── Re-exports so consumers only import from this common module ───────────────
__all__ = [
    "WalletStatus",
    "WalletType",
    "WalletTransactionType",
    "RewardType",
    "Currency",
    "BalanceSummarySchema",
]


class BalanceSummarySchema(BaseSchema):
    """
    Structured snapshot of all wallet balance buckets.

    Returned as a nested object in wallet responses and admin dashboards
    to make client-side rendering straightforward without field-picking.
    """

    available: MoneyAmount = Field(
        description="Cleared credits the customer can spend at checkout.",
    )
    pending: MoneyAmount = Field(
        description="Credits awaiting clearance (e.g., refund pending gateway).",
    )
    locked: MoneyAmount = Field(
        description="Reserved mid-transaction; released on success or failure.",
    )
    promotional: MoneyAmount = Field(
        description="Platform-issued promotional credits that may have an expiry.",
    )
    reward_points: Annotated[int, Field(ge=0)] = Field(
        description="Integer loyalty point balance (not directly spendable).",
    )
    total_spendable: MoneyAmount = Field(
        description="Computed: available + promotional (convenience field).",
    )
