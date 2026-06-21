"""
Admin domain — shared types, validators, and enum re-exports.

Import from here instead of importing enums or validators individually
in other admin schema modules.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import Field, field_validator

from app.models.enums import (
    AdminDepartment,
    AdminStatus,
    AuditAction,
    PermissionAction,
    PermissionResource,
)
from app.schemas.base import BaseSchema

# ── Annotated type helpers ─────────────────────────────────────────────────────

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z_]+\.[a-z_]+$")

PermissionCode = Annotated[
    str,
    Field(
        min_length=3,
        max_length=100,
        description=(
            "RBAC permission code in 'resource.action' dot notation. "
            "Examples: 'bookings.read', 'users.ban', 'vendors.write'. "
            "Lowercase, dot-separated, no spaces."
        ),
    ),
]
"""
Annotated string for permission codes in 'resource.action' format.

Validators in create/update schemas use _PERMISSION_CODE_PATTERN to
enforce the format at schema validation time.
"""

__all__ = [
    "PermissionCode",
    # re-exported enums
    "AdminStatus",
    "AdminDepartment",
    "PermissionAction",
    "PermissionResource",
    "AuditAction",
]
