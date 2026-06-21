"""
Wallet domain — filter query parameter schemas.

These are used by FastAPI endpoints as query-parameter models (via Depends)
and by the repository layer to build WHERE clauses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import RewardType, WalletTransactionType
from app.schemas.base import BaseSchema

__all__ = [
    "WalletTransactionFilters",
    "UserRewardFilters",
]


class WalletTransactionFilters(BaseSchema):
    """
    Filter parameters for the wallet transaction ledger list endpoint.

    All fields are optional; omitting a field means no constraint on that column.
    from_date and to_date filter on the transaction's created_at timestamp.
    """

    wallet_id: uuid.UUID | None = Field(
        default=None,
        description="Restrict to transactions belonging to this wallet.",
    )
    transaction_type: WalletTransactionType | None = Field(
        default=None,
        description="Restrict to a specific transaction category.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Include only transactions created at or after this timestamp (UTC).",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Include only transactions created at or before this timestamp (UTC).",
    )
    reference_type: str | None = Field(
        default=None,
        max_length=100,
        description="Restrict to transactions linked to a specific entity type.",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="Restrict to the transaction linked to this specific entity UUID.",
    )


class UserRewardFilters(BaseSchema):
    """
    Filter parameters for the rewards history list endpoint.

    Supports filtering by credit state, reward category, and date range.
    """

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter rewards belonging to this user.",
    )
    wallet_id: uuid.UUID | None = Field(
        default=None,
        description="Filter rewards belonging to this wallet.",
    )
    reward_type: RewardType | None = Field(
        default=None,
        description="Restrict to a specific reward category.",
    )
    is_credited: bool | None = Field(
        default=None,
        description="True = only credited; False = only pending; None = all.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Include only rewards created at or after this timestamp (UTC).",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Include only rewards created at or before this timestamp (UTC).",
    )
