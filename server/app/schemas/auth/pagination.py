"""
Auth domain — paginated list response types.

Uses the generic CursorPage container from app.schemas.base.
Import these types from here rather than constructing CursorPage[X]
inline in route handlers so that OpenAPI schema generation produces
a stable, named schema.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.auth.response import (
    OTPSentResponse,
    OTPVerifyResponse,
    RefreshTokenResponse,
    SessionResponse,
)

__all__ = [
    "OTPPage",
    "SessionPage",
    "RefreshTokenPage",
]


# CursorPage is Generic[T]; instantiating it with a concrete type produces
# a fully-typed, OpenAPI-compatible model alias.

OTPPage = CursorPage[OTPSentResponse]
"""Paginated list of OTP records (public view, no sensitive fields)."""

SessionPage = CursorPage[SessionResponse]
"""Paginated list of user sessions (public view, no sensitive tokens)."""

RefreshTokenPage = CursorPage[RefreshTokenResponse]
"""Paginated list of refresh tokens (public view, no token hashes)."""
