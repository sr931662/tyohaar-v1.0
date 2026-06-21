"""
Wallet domain — internal / admin-only schemas.

These schemas expose sensitive fields (audit context, admin action metadata)
that MUST NOT appear in public API responses. They are used only by:
- Admin panel endpoints (requires ADMIN or SUPER_ADMIN role)
- Internal service-to-service calls within the backend
- Background jobs (reward crediting, balance reconciliation)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.models.wallets.wallet import WalletStatus
from app.schemas.base import BaseSchema
from app.schemas.wallets.response import WalletResponse

__all__ = [
    "WalletInternal",
    "WalletAdminAction",
]


class WalletInternal(WalletResponse):
    """
    Full wallet representation for admin and internal service use.

    Extends the public WalletResponse with audit-only fields that would
    leak operational context if returned to end-users.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Soft-delete / audit context (never exposed publicly)
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft-delete timestamp; None means wallet is active.",
    )
    # Reconciliation helpers
    last_reconciled_at: datetime | None = Field(
        default=None,
        description="Timestamp of last ledger-vs-balance reconciliation job run.",
    )
    reconciliation_delta: Decimal | None = Field(
        default=None,
        decimal_places=2,
        description="Difference detected during last reconciliation (should be 0.00).",
    )


class WalletAdminAction(BaseSchema):
    """
    Input schema for admin-initiated wallet freeze / suspend / close actions.

    The `action` field drives the new wallet_status; `reason` is mandatory
    for all destructive state changes and is appended to the audit log.
    """

    wallet_id: uuid.UUID = Field(description="Target wallet UUID.")
    action: WalletStatus = Field(
        description=(
            "Desired new status. Allowed values: FROZEN, SUSPENDED, CLOSED. "
            "ACTIVE is used to unfreeze / re-activate a wallet."
        ),
    )
    reason: str = Field(
        min_length=10,
        max_length=1000,
        description="Mandatory justification recorded in the audit log.",
    )
    notifiy_user: bool = Field(
        default=True,
        description="Whether to send an in-app notification to the wallet owner.",
    )
    actioned_by_id: uuid.UUID = Field(
        description="UUID of the admin user performing this action.",
    )
