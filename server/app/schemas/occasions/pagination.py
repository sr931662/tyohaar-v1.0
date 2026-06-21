"""
Paginated list response types for the occasions domain.

Each type alias wires a CursorPage to the appropriate response schema
so FastAPI can generate accurate OpenAPI response models.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.occasions.response import (
    OccasionResponse,
    CelebrationResponse,
    CelebrationGuestResponse,
)

__all__ = [
    "OccasionPage",
    "CelebrationPage",
    "CelebrationGuestPage",
]

OccasionPage = CursorPage[OccasionResponse]
"""Paginated catalogue of occasion types."""

CelebrationPage = CursorPage[CelebrationResponse]
"""Paginated list of customer celebrations."""

CelebrationGuestPage = CursorPage[CelebrationGuestResponse]
"""Paginated guest list for a single celebration."""
