"""
Analytics & Business Intelligence Schemas
==========================================
Response shapes for the Executive Dashboard and all chart APIs.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Shared primitives ─────────────────────────────────────────────────────────

class MetricCard(_Base):
    value: Decimal | int | float
    label: str
    change_pct: float | None = Field(None, description="% change vs previous period")
    trend: str | None = Field(None, description="up | down | flat")


class TimeSeriesPoint(_Base):
    date: str
    value: Decimal | int | float
    label: str | None = None


class CategoryBreakdown(_Base):
    label: str
    value: Decimal | int | float
    pct: float | None = None
    color: str | None = None


# ── Revenue ───────────────────────────────────────────────────────────────────

class RevenueMetrics(_Base):
    today: Decimal
    yesterday: Decimal
    this_week: Decimal
    this_month: Decimal
    this_year: Decimal
    total_lifetime: Decimal
    growth_pct_wow: float
    growth_pct_mom: float
    growth_pct_yoy: float
    average_order_value: Decimal
    currency: str = "INR"


# ── Bookings ──────────────────────────────────────────────────────────────────

class BookingMetrics(_Base):
    total: int
    pending: int
    confirmed: int
    in_progress: int
    completed: int
    cancelled: int
    refunded: int
    rescheduled: int
    completion_rate: float
    cancellation_rate: float
    avg_booking_value: Decimal


# ── Users ─────────────────────────────────────────────────────────────────────

class UserMetrics(_Base):
    total: int
    active: int
    suspended: int
    banned: int
    deactivated: int
    new_today: int
    new_this_week: int
    new_this_month: int
    daily_active: int
    monthly_active: int
    returning_users: int
    retention_rate: float


# ── Vendors ───────────────────────────────────────────────────────────────────

class VendorMetrics(_Base):
    total: int
    verified: int
    pending_approval: int
    rejected: int
    suspended: int
    inactive: int
    new_this_month: int
    avg_rating: float
    avg_bookings_per_vendor: float
    top_vendors: list[dict[str, Any]]


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentMetrics(_Base):
    total_transactions: int
    successful: int
    failed: int
    refunded: int
    pending: int
    total_volume: Decimal
    total_refunded: Decimal
    gateway_success_rate: float
    avg_transaction_value: Decimal


# ── Memberships ───────────────────────────────────────────────────────────────

class MembershipMetrics(_Base):
    total_active: int
    expired_this_month: int
    renewed_this_month: int
    new_subscriptions_this_month: int
    conversion_rate: float
    monthly_recurring_revenue: Decimal
    churn_rate: float
    plan_breakdown: list[CategoryBreakdown]


# ── Referrals ─────────────────────────────────────────────────────────────────

class ReferralMetrics(_Base):
    total_referrals: int
    successful_referrals: int
    pending_referrals: int
    referral_conversion_rate: float
    total_referral_revenue: Decimal
    total_rewards_issued: Decimal


# ── Support ───────────────────────────────────────────────────────────────────

class SupportMetrics(_Base):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    avg_resolution_hours: float
    sla_breach_count: int
    priority_breakdown: list[CategoryBreakdown]


# ── Media ─────────────────────────────────────────────────────────────────────

class MediaMetrics(_Base):
    total_images: int
    total_videos: int
    pending_moderation: int
    approved: int
    rejected: int
    total_storage_mb: float
    uploads_this_month: int


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationMetrics(_Base):
    total_sent: int
    push_sent: int
    email_sent: int
    sms_sent: int
    in_app_sent: int
    delivery_rate: float
    read_rate: float
    avg_ctr: float


# ── Budgets ───────────────────────────────────────────────────────────────────

class BudgetMetrics(_Base):
    total_budgets: int
    avg_budget_amount: Decimal
    avg_utilization_pct: float
    over_budget_count: int
    category_distribution: list[CategoryBreakdown]


# ── Occasions ─────────────────────────────────────────────────────────────────

class OccasionMetrics(_Base):
    total_celebrations: int
    celebrations_this_month: int
    most_popular_occasion: str | None
    most_popular_occasion_count: int
    occasion_breakdown: list[CategoryBreakdown]
    trending_packages: list[dict[str, Any]]


# ── Geographic ────────────────────────────────────────────────────────────────

class CityMetric(_Base):
    city: str
    state: str | None = None
    bookings: int
    revenue: Decimal
    active_vendors: int
    growth_pct: float


class GeographicMetrics(_Base):
    top_cities: list[CityMetric]
    revenue_by_state: list[CategoryBreakdown]
    booking_heat: list[dict[str, Any]]


# ── Platform Health ───────────────────────────────────────────────────────────

class PlatformHealth(_Base):
    active_sessions: int
    api_requests_today: int
    database_status: str
    avg_response_ms: float
    error_rate_pct: float
    uptime_pct: float


# ── Executive Dashboard (aggregate) ──────────────────────────────────────────

class ExecutiveDashboard(_Base):
    generated_at: datetime
    period_label: str
    revenue: RevenueMetrics
    bookings: BookingMetrics
    users: UserMetrics
    vendors: VendorMetrics
    payments: PaymentMetrics
    memberships: MembershipMetrics
    referrals: ReferralMetrics
    occasions: OccasionMetrics
    support: SupportMetrics
    media: MediaMetrics
    notifications: NotificationMetrics
    budgets: BudgetMetrics
    geographic: GeographicMetrics
    platform_health: PlatformHealth
    pending_actions: dict[str, int]


# ── Chart Schemas ─────────────────────────────────────────────────────────────

class ChartData(_Base):
    chart_type: str
    title: str
    x_label: str | None = None
    y_label: str | None = None
    series: list[dict[str, Any]]
    annotations: list[dict[str, Any]] | None = None


class TimeSeriesChart(_Base):
    title: str
    granularity: str
    series: list[dict[str, Any]]
    date_range: dict[str, str]


class PieChartData(_Base):
    title: str
    segments: list[CategoryBreakdown]
    total: Decimal | int


class HeatmapData(_Base):
    title: str
    rows: list[str]
    columns: list[str]
    values: list[list[float | int]]


class ForecastData(_Base):
    metric: str
    historical: list[TimeSeriesPoint]
    forecast: list[TimeSeriesPoint]
    confidence_interval: dict[str, list[float]] | None = None


# ── Widget cards ──────────────────────────────────────────────────────────────

class DashboardWidget(_Base):
    widget_id: str
    title: str
    value: Any
    change_pct: float | None = None
    trend: str | None = None
    icon: str | None = None
    color: str | None = None
    link: str | None = None


class ActivityItem(_Base):
    type: str
    entity_id: str
    entity_type: str
    summary: str
    actor: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] | None = None


class ActivityFeed(_Base):
    items: list[ActivityItem]
    has_more: bool
