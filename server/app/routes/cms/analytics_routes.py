"""Analytics endpoints — /admin/cms/analytics/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.analytics_controller import (
    AnalyticsServiceDep,
    get_activity_feed,
    get_booking_metrics,
    get_bookings_chart,
    get_category_distribution,
    get_dashboard_widgets,
    get_executive_dashboard,
    get_geographic_metrics,
    get_payment_metrics,
    get_pending_actions,
    get_platform_health,
    get_revenue_chart,
    get_revenue_metrics,
    get_support_metrics,
    get_user_metrics,
    get_users_chart,
    get_vendor_metrics,
)

router = APIRouter(prefix="/analytics", tags=["CMS — Analytics"])

router.add_api_route(
    "/dashboard",
    get_executive_dashboard,
    methods=["GET"],
    summary="Executive dashboard — all metrics",
)
router.add_api_route(
    "/revenue",
    get_revenue_metrics,
    methods=["GET"],
    summary="Revenue metrics",
)
router.add_api_route(
    "/bookings",
    get_booking_metrics,
    methods=["GET"],
    summary="Booking metrics",
)
router.add_api_route(
    "/users",
    get_user_metrics,
    methods=["GET"],
    summary="User metrics",
)
router.add_api_route(
    "/vendors",
    get_vendor_metrics,
    methods=["GET"],
    summary="Vendor metrics",
)
router.add_api_route(
    "/payments",
    get_payment_metrics,
    methods=["GET"],
    summary="Payment metrics",
)
router.add_api_route(
    "/support",
    get_support_metrics,
    methods=["GET"],
    summary="Support metrics",
)
router.add_api_route(
    "/platform-health",
    get_platform_health,
    methods=["GET"],
    summary="Platform health indicators",
)
router.add_api_route(
    "/geographic",
    get_geographic_metrics,
    methods=["GET"],
    summary="Geographic / city metrics",
)
router.add_api_route(
    "/pending-actions",
    get_pending_actions,
    methods=["GET"],
    summary="Counts of items needing admin action",
)

# ── Charts ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/charts/revenue",
    get_revenue_chart,
    methods=["GET"],
    summary="Revenue time-series chart",
)
router.add_api_route(
    "/charts/bookings",
    get_bookings_chart,
    methods=["GET"],
    summary="Bookings time-series chart by status",
)
router.add_api_route(
    "/charts/users",
    get_users_chart,
    methods=["GET"],
    summary="User registrations time-series chart",
)
router.add_api_route(
    "/charts/categories",
    get_category_distribution,
    methods=["GET"],
    summary="Category distribution pie chart",
)

# ── Activity & Widgets ────────────────────────────────────────────────────────

router.add_api_route(
    "/activity-feed",
    get_activity_feed,
    methods=["GET"],
    summary="Recent platform activity feed",
)
router.add_api_route(
    "/widgets",
    get_dashboard_widgets,
    methods=["GET"],
    summary="Dashboard widget metric cards",
)
