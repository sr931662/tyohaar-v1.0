"""Automation Engine Schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


TRIGGER_EVENTS = [
    "vendor.registered", "vendor.approved", "vendor.rejected",
    "booking.created", "booking.confirmed", "booking.completed", "booking.cancelled",
    "payment.completed", "payment.failed", "payment.refunded",
    "membership.expiring", "membership.expired", "membership.renewed",
    "user.registered", "user.inactive", "referral.completed",
    "support.ticket_opened", "support.ticket_resolved",
]

ACTION_TYPES = [
    "send_notification", "send_email", "send_sms",
    "generate_invoice", "wallet_credit", "wallet_settlement",
    "assign_membership", "apply_coupon", "create_support_ticket",
    "update_vendor_status", "update_user_status",
    "trigger_webhook", "log_event",
]


class AutomationActionSchema(_Base):
    type: str = Field(..., description="Action type. One of: " + ", ".join(ACTION_TYPES))
    params: dict[str, Any] = Field(default_factory=dict)
    delay_seconds: int = Field(default=0, ge=0)


class AutomationRuleCreate(_Base):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    trigger_event: str = Field(..., description="One of: " + ", ".join(TRIGGER_EVENTS))
    conditions: dict[str, Any] | None = Field(
        default=None,
        description="Optional condition tree. Null = always execute.",
    )
    actions: list[AutomationActionSchema] = Field(..., min_length=1, max_length=20)
    is_active: bool = Field(default=True)
    priority: int = Field(default=100, ge=1, le=1000)
    delay_seconds: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)


class AutomationRuleUpdate(_Base):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    conditions: dict[str, Any] | None = None
    actions: list[AutomationActionSchema] | None = None
    is_active: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)
    delay_seconds: int | None = Field(default=None, ge=0)
    max_retries: int | None = Field(default=None, ge=0, le=10)


class AutomationRuleResponse(_Base):
    id: uuid.UUID
    created_by_admin_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    trigger_event: str
    conditions: dict[str, Any] | None = None
    actions: list[dict[str, Any]]
    is_active: bool
    priority: int
    delay_seconds: int
    max_retries: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    last_triggered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AutomationLogResponse(_Base):
    id: uuid.UUID
    rule_id: uuid.UUID
    rule_name: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    trigger_event: str
    status: str
    actions_total: int
    actions_completed: int
    actions_failed: int
    action_results: list[dict[str, Any]] | None = None
    retry_count: int
    error_message: str | None = None
    duration_ms: int | None = None
    completed_at: datetime | None = None
    created_at: datetime


class AutomationManualTriggerRequest(_Base):
    entity_id: str | None = Field(default=None, description="Optional entity to scope the trigger")
    entity_type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AutomationToggleResponse(_Base):
    rule_id: uuid.UUID
    is_active: bool
    message: str
