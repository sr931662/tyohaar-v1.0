"""
Referrals domain schema package.

Single stable import entry point:

    from app.schemas.referrals import ReferralCreate, ReferralResponse, ReferralPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.referrals.common import (
    Currency,
    ReferralChannel,
    ReferralRewardStatus,
    ReferralRewardTrigger,
    ReferralStatus,
    RewardType,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.referrals.create import (
    ReferralCreate,
    ReferralRewardCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.referrals.update import (
    ReferralRewardUpdate,
    ReferralUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.referrals.response import (
    ReferralResponse,
    ReferralRewardResponse,
    ReferralStatsResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.referrals.filters import (
    ReferralFilters,
    ReferralRewardFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.referrals.pagination import (
    ReferralPage,
    ReferralRewardPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.referrals.internal import (
    ReferralFraudReview,
    ReferralInternal,
)

__all__ = [
    # common / enums
    "ReferralChannel",
    "ReferralRewardStatus",
    "ReferralRewardTrigger",
    "ReferralStatus",
    "RewardType",
    "Currency",
    # create
    "ReferralCreate",
    "ReferralRewardCreate",
    # update
    "ReferralUpdate",
    "ReferralRewardUpdate",
    # response
    "ReferralResponse",
    "ReferralRewardResponse",
    "ReferralStatsResponse",
    # filters
    "ReferralFilters",
    "ReferralRewardFilters",
    # pagination
    "ReferralPage",
    "ReferralRewardPage",
    # internal
    "ReferralInternal",
    "ReferralFraudReview",
]
