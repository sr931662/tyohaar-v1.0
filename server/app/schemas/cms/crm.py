"""CRM Schemas — 360° vendor and customer profiles."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Shared ────────────────────────────────────────────────────────────────────

class TimelineEvent(_Base):
    event_type: str
    title: str
    description: str | None = None
    actor: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] | None = None


class PerformanceMonth(_Base):
    year: int
    month: int
    label: str
    bookings: int
    revenue: Decimal
    completion_rate: float
    cancellation_rate: float
    avg_rating: float | None = None


class CRMNote(_Base):
    id: uuid.UUID
    content: str
    author: str
    created_at: datetime
    updated_at: datetime


# ── Vendor CRM ────────────────────────────────────────────────────────────────

class VendorCRMSummary(_Base):
    vendor_id: uuid.UUID
    business_name: str
    owner_name: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    verification_status: str
    account_status: str
    onboarded_at: datetime | None = None
    assigned_manager: str | None = None


class VendorKYC(_Base):
    pan_number: str | None = None
    gst_number: str | None = None
    pan_verified: bool = False
    gst_verified: bool = False
    kyc_status: str
    kyc_verified_at: datetime | None = None
    documents: list[dict[str, Any]]
    certificates: list[dict[str, Any]]


class VendorFinancials(_Base):
    total_revenue_lifetime: Decimal
    revenue_this_month: Decimal
    revenue_last_month: Decimal
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    avg_booking_value: Decimal
    commission_earned_platform: Decimal
    pending_settlement: Decimal
    wallet_balance: Decimal
    settlement_history: list[dict[str, Any]]


class VendorRatings(_Base):
    avg_rating: float
    total_reviews: int
    rating_distribution: dict[str, int]
    recent_reviews: list[dict[str, Any]]


class VendorCRMProfile(_Base):
    summary: VendorCRMSummary
    kyc: VendorKYC
    financials: VendorFinancials
    ratings: VendorRatings
    bank_accounts: list[dict[str, Any]]
    monthly_performance: list[PerformanceMonth]
    recent_bookings: list[dict[str, Any]]
    timeline: list[TimelineEvent]
    notes: str | None = None
    tags: list[str]
    verification_timeline: list[TimelineEvent]


# ── Customer CRM ──────────────────────────────────────────────────────────────

class CustomerCRMSummary(_Base):
    user_id: uuid.UUID
    full_name: str | None = None
    phone: str
    email: str | None = None
    account_status: str
    registered_at: datetime | None = None
    last_login_at: datetime | None = None
    city: str | None = None
    state: str | None = None
    membership_tier: str | None = None


class CustomerFinancials(_Base):
    total_spent_lifetime: Decimal
    spent_this_month: Decimal
    total_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    avg_booking_value: Decimal
    wallet_balance: Decimal
    reward_points: Decimal
    total_refunds_received: Decimal


class CustomerCRMProfile(_Base):
    summary: CustomerCRMSummary
    financials: CustomerFinancials
    active_membership: dict[str, Any] | None = None
    recent_bookings: list[dict[str, Any]]
    recent_payments: list[dict[str, Any]]
    addresses: list[dict[str, Any]]
    referral_stats: dict[str, Any]
    open_support_tickets: int
    recent_notifications: list[dict[str, Any]]
    recent_reviews: list[dict[str, Any]]
    timeline: list[TimelineEvent]


# ── Filters ───────────────────────────────────────────────────────────────────

class VendorCRMFilter(_Base):
    verification_status: str | None = None
    account_status: str | None = None
    city: str | None = None
    min_revenue: Decimal | None = None
    max_revenue: Decimal | None = None
    assigned_manager: str | None = None


class CustomerCRMFilter(_Base):
    account_status: str | None = None
    city: str | None = None
    membership_tier: str | None = None
    min_spent: Decimal | None = None
    max_spent: Decimal | None = None
    registered_from: datetime | None = None
    registered_to: datetime | None = None
