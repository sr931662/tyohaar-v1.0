"""
Budgets domain — internal / service-layer schemas.

These schemas are NEVER returned directly to API clients. They are used
by the service layer, background jobs, and admin-only endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict, Field

from app.schemas.base import IDSchema, MoneyAmount
from app.schemas.budgets.common import (
    BudgetAlertLevel,
    BudgetCategory,
    BudgetHealthStatus,
    BudgetLifecycleStatus,
    Currency,
    ExpenseSource,
    ExpenseType,
)


class BudgetInternal(IDSchema):
    """
    Complete internal representation of a Budget including soft-delete field.

    Used by admin dashboards, data export pipelines, and audit workflows.
    Never serialise directly into a public API response.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    celebration_id: uuid.UUID
    user_id: uuid.UUID
    currency: Currency
    total_planned: MoneyAmount
    total_spent: MoneyAmount
    total_estimated: MoneyAmount
    contingency_pct: Decimal
    contingency_amount: MoneyAmount
    lifecycle_status: BudgetLifecycleStatus
    health_status: BudgetHealthStatus
    alert_threshold_pct: Decimal
    alert_level: BudgetAlertLevel | None = None
    notes: str | None = None

    created_at: datetime
    updated_at: datetime
    # Soft-delete field — internal only, never exposed publicly
    deleted_at: datetime | None = None


class BudgetHealthUpdate(IDSchema):
    """
    Service-layer payload for updating computed budget health fields.

    Applied by the expense aggregation service whenever an expense is
    created, updated, or deleted. Keeps derived budget fields in sync
    without a full model round-trip.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    health_status: BudgetHealthStatus = Field(
        description="Recomputed spending health indicator"
    )
    alert_level: BudgetAlertLevel | None = Field(
        default=None,
        description="Recomputed alert severity; None when no alert is active",
    )
    total_spent: MoneyAmount = Field(
        description="Recomputed sum of all ACTUAL expenses"
    )
    total_estimated: MoneyAmount = Field(
        description="Recomputed sum of all ESTIMATED expenses"
    )


__all__ = [
    "BudgetInternal",
    "BudgetHealthUpdate",
]
