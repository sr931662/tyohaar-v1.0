"""
Memberships domain — shared types and enum re-exports.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.models.enums import (
    Currency,
    MembershipBillingCycle,
    MembershipStatus,
    MembershipTier,
)
from app.schemas.base import BaseSchema, MoneyAmount

__all__ = [
    "MembershipTier",
    "MembershipStatus",
    "MembershipBillingCycle",
    "Currency",
    "PlanBenefitSchema",
]


class PlanBenefitSchema(BaseSchema):
    """
    Structured representation of a single membership plan benefit.

    Plans carry a flexible JSONB `benefits` column for future-proof
    benefit definitions. This schema provides a typed view for rendering
    benefit lists in plan comparison UIs.
    """

    key: str = Field(
        max_length=100,
        description="Machine-readable benefit identifier, e.g. 'free_delivery'.",
    )
    label: str = Field(
        max_length=200,
        description="Human-readable benefit name shown in plan comparison cards.",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional elaboration displayed in tooltips or expanded views.",
    )
    value: Any | None = Field(
        default=None,
        description="Scalar or structured value (e.g. '20%', 5, True).",
    )
    is_highlighted: bool = Field(
        default=False,
        description="Whether this benefit should be visually highlighted in the UI.",
    )
