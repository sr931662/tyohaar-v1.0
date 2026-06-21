"""
Auth schemas package.

Re-exports every public symbol from the seven sub-modules so that
consumers can write:

    from app.schemas.auth import OTPRequestCreate, SessionResponse, ...

instead of importing from individual submodules.
"""

from __future__ import annotations

from app.schemas.auth.common import (
    DeviceInfoSchema,
    DeviceType,
    LocationInfoSchema,
    LoginMethod,
    OTPCode,
    OTPDeliveryChannel,
    OTPIdentifier,
    OTPPurpose,
    OTPStatus,
    Platform,
    SessionStatus,
    TokenRevocationReason,
    validate_otp_identifier,
)
from app.schemas.auth.create import (
    OTPRequestCreate,
    OTPVerifyCreate,
    RefreshTokenCreate,
    SessionCreate,
)
from app.schemas.auth.filters import (
    OTPFilters,
    RefreshTokenFilters,
    SessionFilters,
)
from app.schemas.auth.internal import (
    OTPInternal,
    RefreshTokenInternal,
    SessionInternal,
)
from app.schemas.auth.pagination import (
    OTPPage,
    RefreshTokenPage,
    SessionPage,
)
from app.schemas.auth.response import (
    OTPSentResponse,
    OTPVerifyResponse,
    RefreshTokenResponse,
    SessionResponse,
)
from app.schemas.auth.update import (
    RefreshTokenUpdate,
    SessionUpdate,
)

__all__ = [
    # ── Enums ──────────────────────────────────────────────────────────────────
    "OTPDeliveryChannel",
    "OTPPurpose",
    "OTPStatus",
    "SessionStatus",
    "LoginMethod",
    "DeviceType",
    "Platform",
    "TokenRevocationReason",
    # ── Common types & helpers ─────────────────────────────────────────────────
    "OTPIdentifier",
    "OTPCode",
    "validate_otp_identifier",
    "DeviceInfoSchema",
    "LocationInfoSchema",
    # ── Create ────────────────────────────────────────────────────────────────
    "OTPRequestCreate",
    "OTPVerifyCreate",
    "SessionCreate",
    "RefreshTokenCreate",
    # ── Update ────────────────────────────────────────────────────────────────
    "SessionUpdate",
    "RefreshTokenUpdate",
    # ── Response ──────────────────────────────────────────────────────────────
    "OTPSentResponse",
    "OTPVerifyResponse",
    "SessionResponse",
    "RefreshTokenResponse",
    # ── Filters ───────────────────────────────────────────────────────────────
    "OTPFilters",
    "SessionFilters",
    "RefreshTokenFilters",
    # ── Pagination ────────────────────────────────────────────────────────────
    "OTPPage",
    "SessionPage",
    "RefreshTokenPage",
    # ── Internal ──────────────────────────────────────────────────────────────
    "OTPInternal",
    "SessionInternal",
    "RefreshTokenInternal",
]
