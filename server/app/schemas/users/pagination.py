"""
Users domain — paginated list response types.

Uses the generic CursorPage container from app.schemas.base.
Import these aliases from here so that OpenAPI schema generation
produces stable, named schemas rather than anonymous generics.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.users.response import (
    UserAddressResponse,
    UserDeviceResponse,
    UserResponse,
)

__all__ = [
    "UserPage",
    "UserAddressPage",
    "UserDevicePage",
]


UserPage = CursorPage[UserResponse]
"""Paginated list of user records (public view, no sensitive fields)."""

UserAddressPage = CursorPage[UserAddressResponse]
"""Paginated list of user address records."""

UserDevicePage = CursorPage[UserDeviceResponse]
"""Paginated list of user device records (no push tokens)."""
