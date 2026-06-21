"""
Wallets domain schema package.

Single stable import entry point:

    from app.schemas.wallets import WalletCreate, WalletResponse, WalletTransactionPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.wallets.common import (
    BalanceSummarySchema,
    Currency,
    RewardType,
    WalletStatus,
    WalletTransactionType,
    WalletType,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.wallets.create import (
    UserRewardCreate,
    WalletCreate,
    WalletTransactionCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.wallets.update import (
    UserRewardUpdate,
    WalletTransactionUpdate,
    WalletUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.wallets.response import (
    UserRewardResponse,
    WalletResponse,
    WalletTransactionResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.wallets.filters import (
    UserRewardFilters,
    WalletTransactionFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.wallets.pagination import (
    UserRewardPage,
    WalletTransactionPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.wallets.internal import (
    WalletAdminAction,
    WalletInternal,
)

__all__ = [
    # common
    "WalletStatus",
    "WalletType",
    "WalletTransactionType",
    "RewardType",
    "Currency",
    "BalanceSummarySchema",
    # create
    "WalletCreate",
    "WalletTransactionCreate",
    "UserRewardCreate",
    # update
    "WalletUpdate",
    "WalletTransactionUpdate",
    "UserRewardUpdate",
    # response
    "WalletResponse",
    "WalletTransactionResponse",
    "UserRewardResponse",
    # filters
    "WalletTransactionFilters",
    "UserRewardFilters",
    # pagination
    "WalletTransactionPage",
    "UserRewardPage",
    # internal
    "WalletInternal",
    "WalletAdminAction",
]
