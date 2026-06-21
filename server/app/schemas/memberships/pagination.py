"""
Memberships domain — paginated list response schemas.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.memberships.response import MembershipPlanResponse, UserMembershipResponse

__all__ = [
    "MembershipPlanPage",
    "UserMembershipPage",
]

MembershipPlanPage = CursorPage[MembershipPlanResponse]
UserMembershipPage = CursorPage[UserMembershipResponse]
