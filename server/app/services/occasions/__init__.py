"""
Occasions service package.

Stable import surface:

    from app.services.occasions import OccasionService
    from app.services.occasions.exceptions import CelebrationNotFoundError, ...
    from app.services.occasions.constants import MAX_GUESTS_PER_CELEBRATION, ...
"""

from __future__ import annotations

from app.services.occasions.service import OccasionService

__all__ = ["OccasionService"]
