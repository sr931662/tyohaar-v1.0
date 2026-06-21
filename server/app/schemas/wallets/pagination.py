"""
Wallet domain — paginated list response schemas.

All list responses use keyset (cursor) pagination via CursorPage for
O(1) performance regardless of offset depth.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.wallets.response import UserRewardResponse, WalletTransactionResponse

__all__ = [
    "WalletTransactionPage",
    "UserRewardPage",
]

# Concrete instantiations of the generic CursorPage for OpenAPI schema generation.
WalletTransactionPage = CursorPage[WalletTransactionResponse]
UserRewardPage = CursorPage[UserRewardResponse]
