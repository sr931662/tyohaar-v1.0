"""
Referrals domain — paginated list response schemas.

Both use keyset (cursor-based) pagination via CursorPage for O(1) performance
at scale. Pass next_cursor verbatim to the next request to advance pages.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.referrals.response import ReferralResponse, ReferralRewardResponse

# CursorPage[T] provides: items, next_cursor, has_more, total

ReferralPage = CursorPage[ReferralResponse]
"""Paginated list of referrals."""

ReferralRewardPage = CursorPage[ReferralRewardResponse]
"""Paginated list of referral reward records."""

__all__ = [
    "ReferralPage",
    "ReferralRewardPage",
]
