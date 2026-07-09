"""
Occasions domain schema package.

Import from here for a single, stable entry point:

    from app.schemas.occasions import CelebrationCreate, CelebrationResponse, OccasionPage
"""

from __future__ import annotations

# ── common ────────────────────────────────────────────────────────────────────
from app.schemas.occasions.common import (
    TimeSlotSchema,
    VenueSchema,
    # enums
    OccasionCategory,
    CelebrationStatus,
    Currency,
    RSVPStatus,
)

# ── create ────────────────────────────────────────────────────────────────────
from app.schemas.occasions.create import (
    CelebrationCreate,
    CelebrationGuestCreate,
    CelebrationChecklistCreate,
    OccasionCreate,
    GuestRSVPSubmit,
)

# ── update ────────────────────────────────────────────────────────────────────
from app.schemas.occasions.update import (
    CelebrationUpdate,
    CelebrationGuestUpdate,
    CelebrationChecklistUpdate,
)

# ── response ──────────────────────────────────────────────────────────────────
from app.schemas.occasions.response import (
    OccasionResponse,
    OccasionThemeResponse,
    OccasionMoodResponse,
    OccasionTagResponse,
    CelebrationResponse,
    CelebrationGuestResponse,
    CelebrationChecklistResponse,
    GuestRSVPPublicResponse,
)

# ── filters ───────────────────────────────────────────────────────────────────
from app.schemas.occasions.filters import (
    CelebrationFilters,
    OccasionFilters,
)

# ── pagination ────────────────────────────────────────────────────────────────
from app.schemas.occasions.pagination import (
    OccasionPage,
    CelebrationPage,
    CelebrationGuestPage,
)

# ── internal (admin) ──────────────────────────────────────────────────────────
from app.schemas.occasions.internal import (
    CelebrationInternal,
    CelebrationSummary,
)

__all__ = [
    # common
    "TimeSlotSchema",
    "VenueSchema",
    "OccasionCategory",
    "CelebrationStatus",
    "Currency",
    "RSVPStatus",
    # create
    "CelebrationCreate",
    "CelebrationGuestCreate",
    "CelebrationChecklistCreate",
    "OccasionCreate",
    "GuestRSVPSubmit",
    # update
    "CelebrationUpdate",
    "CelebrationGuestUpdate",
    "CelebrationChecklistUpdate",
    # response
    "OccasionResponse",
    "OccasionThemeResponse",
    "OccasionMoodResponse",
    "OccasionTagResponse",
    "CelebrationResponse",
    "CelebrationGuestResponse",
    "CelebrationChecklistResponse",
    "GuestRSVPPublicResponse",
    # filters
    "CelebrationFilters",
    "OccasionFilters",
    # pagination
    "OccasionPage",
    "CelebrationPage",
    "CelebrationGuestPage",
    # internal
    "CelebrationInternal",
    "CelebrationSummary",
]
