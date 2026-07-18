"""Bulk Operations Schemas."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BulkIDsRequest(_Base):
    ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    reason: str | None = Field(default=None, max_length=500)


class BulkVendorActionRequest(BulkIDsRequest):
    note: str | None = Field(default=None, max_length=1000)


class BulkPackageActionRequest(BulkIDsRequest):
    pass


class BulkDiscountActionRequest(BulkIDsRequest):
    pass


class BulkPriceUpdateRequest(_Base):
    ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    adjustment_type: str = Field(..., description="FIXED | PERCENTAGE")
    adjustment_value: Decimal = Field(..., description="Amount to add/subtract or % change")
    direction: str = Field(default="INCREASE", description="INCREASE | DECREASE")


class BulkAvailabilityUpdateRequest(_Base):
    vendor_ids: list[uuid.UUID] = Field(default_factory=list)
    package_ids: list[uuid.UUID] = Field(default_factory=list)
    date: str = Field(..., description="YYYY-MM-DD")
    is_available: bool


class BulkNotificationRequest(_Base):
    user_ids: list[uuid.UUID] = Field(default_factory=list)
    send_to_all: bool = Field(default=False)
    roles: list[str] = Field(default_factory=list)
    title: str = Field(..., max_length=255)
    body: str = Field(..., max_length=1000)
    channels: list[str] = Field(default_factory=lambda: ["IN_APP"])
    data: dict[str, Any] | None = None


class BulkCouponGenerateRequest(_Base):
    count: int = Field(..., ge=1, le=1000)
    prefix: str = Field(default="TYO", max_length=10)
    discount_type: str = Field(
        default="percentage",
        description="One of the Coupon.coupon_type values: percentage | fixed_amount | fixed_price | free_service | cashback",
    )
    discount_value: Decimal
    max_uses: int = Field(default=1, description="total_usage_limit for each generated code")
    valid_from: str
    valid_until: str
    min_order_value: Decimal = Field(default=Decimal("0"))


class BulkMembershipAssignRequest(_Base):
    user_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    plan_id: uuid.UUID
    duration_days: int = Field(default=30, ge=1)
    reason: str | None = None


class BulkOperationResult(_Base):
    operation: str
    total_requested: int
    succeeded: int
    failed: int
    skipped: int
    errors: list[dict[str, Any]]
    processed_ids: list[str]
    failed_ids: list[str]
