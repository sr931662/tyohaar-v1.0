"""
Memberships domain schema package.

Single stable import entry point:

    from app.schemas.memberships import MembershipPlanCreate, UserMembershipResponse
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.memberships.common import (
    Currency,
    MembershipBillingCycle,
    MembershipStatus,
    MembershipTier,
    PlanBenefitSchema,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.memberships.create import (
    MembershipPlanCreate,
    UserMembershipCreate,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.memberships.update import (
    MembershipPlanUpdate,
    UserMembershipUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.memberships.response import (
    MembershipPlanResponse,
    UserMembershipResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.memberships.filters import (
    MembershipPlanFilters,
    UserMembershipFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.memberships.pagination import (
    MembershipPlanPage,
    UserMembershipPage,
)

# ── internal ──────────────────────────────────────────────────────────────────
from app.schemas.memberships.internal import (
    MembershipPlanInternal,
    UserMembershipInternal,
)

__all__ = [
    # common
    "MembershipTier",
    "MembershipStatus",
    "MembershipBillingCycle",
    "Currency",
    "PlanBenefitSchema",
    # create
    "MembershipPlanCreate",
    "UserMembershipCreate",
    # update
    "MembershipPlanUpdate",
    "UserMembershipUpdate",
    # response
    "MembershipPlanResponse",
    "UserMembershipResponse",
    # filters
    "MembershipPlanFilters",
    "UserMembershipFilters",
    # pagination
    "MembershipPlanPage",
    "UserMembershipPage",
    # internal
    "MembershipPlanInternal",
    "UserMembershipInternal",
]
