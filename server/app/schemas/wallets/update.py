"""
Wallet domain — update (patch) schemas.

All fields are Optional because these are used for partial PATCH semantics.
WalletTransaction records are largely immutable by design (append-only ledger);
only non-financial fields are patchable.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.wallets.wallet import WalletStatus
from app.schemas.base import BaseSchema

__all__ = [
    "WalletUpdate",
    "WalletTransactionUpdate",
    "UserRewardUpdate",
]


class WalletUpdate(BaseSchema):
    """
    Admin-only patch schema for wallet lifecycle management.

    Balance fields are NEVER updated via this schema — they are computed
    by the transaction ledger. Only status fields may be changed here.
    """

    wallet_status: WalletStatus | None = Field(
        default=None,
        description="Lifecycle state of the wallet (ACTIVE / FROZEN / SUSPENDED / CLOSED).",
    )
    is_on_hold: bool | None = Field(
        default=None,
        description="Emergency hold flag; blocks all debits without changing wallet_status.",
    )


class WalletTransactionUpdate(BaseSchema):
    """
    Restricted patch schema for wallet transaction records.

    Transaction records form an immutable ledger — only the human-readable
    description field may be amended (e.g. for compliance note corrections).
    Financial fields (amount, balance_before, balance_after) are never patched.
    """

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Amended human-readable description for compliance purposes.",
    )


class UserRewardUpdate(BaseSchema):
    """
    Patch schema for reward lifecycle management.

    Used by the reward processing job to mark rewards as credited and
    by admin tools to adjust expiry dates.
    """

    is_credited: bool | None = Field(
        default=None,
        description="Set to True once the reward amount has been credited to the wallet.",
    )
    credited_at: datetime | None = Field(
        default=None,
        description="Timestamp when the reward was credited. Required if is_credited=True.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Updated expiry date for promotional reward grants.",
    )
