"""
Users schemas package.

Re-exports every public symbol from the seven sub-modules so that
consumers can write:

    from app.schemas.users import UserCreate, UserResponse, UserPage, ...

instead of importing from individual submodules.
"""

from __future__ import annotations

from app.schemas.users.common import (
    AccountStatus,
    AddressType,
    Currency,
    DeviceType,
    DisplayNameSchema,
    EmergencyContactSchema,
    Gender,
    Language,
    LocationSchema,
    LoginMethod,
    PhoneNumber,
    Platform,
    UserRole,
    UserType,
    VerificationStatus,
    normalize_phone,
)
from app.schemas.users.create import (
    UserAddressCreate,
    UserCreate,
    UserDeviceCreate,
    UserProfileCreate,
)
from app.schemas.users.filters import (
    UserAddressFilters,
    UserDeviceFilters,
    UserFilters,
)
from app.schemas.users.internal import (
    UserAdminStats,
    UserDeviceInternal,
    UserInternal,
    UserProfileInternal,
)
from app.schemas.users.pagination import (
    UserAddressPage,
    UserDevicePage,
    UserPage,
)
from app.schemas.users.response import (
    UserAddressResponse,
    UserDeviceResponse,
    UserProfileResponse,
    UserPublicResponse,
    UserResponse,
)
from app.schemas.users.update import (
    UserAddressUpdate,
    UserDeviceUpdate,
    UserProfileUpdate,
    UserUpdate,
)

__all__ = [
    # ── Enums ──────────────────────────────────────────────────────────────────
    "UserRole",
    "UserType",
    "AccountStatus",
    "VerificationStatus",
    "LoginMethod",
    "Gender",
    "Language",
    "Currency",
    "AddressType",
    "DeviceType",
    "Platform",
    # ── Common types & helpers ─────────────────────────────────────────────────
    "PhoneNumber",
    "normalize_phone",
    "DisplayNameSchema",
    "LocationSchema",
    "EmergencyContactSchema",
    # ── Create ────────────────────────────────────────────────────────────────
    "UserCreate",
    "UserProfileCreate",
    "UserAddressCreate",
    "UserDeviceCreate",
    # ── Update ────────────────────────────────────────────────────────────────
    "UserUpdate",
    "UserProfileUpdate",
    "UserAddressUpdate",
    "UserDeviceUpdate",
    # ── Response ──────────────────────────────────────────────────────────────
    "UserResponse",
    "UserPublicResponse",
    "UserProfileResponse",
    "UserAddressResponse",
    "UserDeviceResponse",
    # ── Filters ───────────────────────────────────────────────────────────────
    "UserFilters",
    "UserAddressFilters",
    "UserDeviceFilters",
    # ── Pagination ────────────────────────────────────────────────────────────
    "UserPage",
    "UserAddressPage",
    "UserDevicePage",
    # ── Internal ──────────────────────────────────────────────────────────────
    "UserInternal",
    "UserProfileInternal",
    "UserDeviceInternal",
    "UserAdminStats",
]
