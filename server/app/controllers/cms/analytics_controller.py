"""Analytics CMS controller functions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from app.core.responses import SuccessResponse
from app.schemas.cms.analytics import (
    ActivityFeed,
    BookingMetrics,
    ChartData,
    DashboardWidget,
    ExecutiveDashboard,
    GeographicMetrics,
    PaymentMetrics,
    PieChartData,
    PlatformHealth,
    RevenueMetrics,
    SupportMetrics,
    TimeSeriesChart,
    UserMetrics,
    VendorMetrics,
    WalletMetrics,
)
from app.services.cms.analytics_service import AnalyticsService


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


async def get_executive_dashboard(svc: AnalyticsServiceDep) -> SuccessResponse[ExecutiveDashboard]:
    data = await svc.get_executive_dashboard()
    return SuccessResponse(data=data, message="Dashboard loaded")


async def get_revenue_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[RevenueMetrics]:
    return SuccessResponse(data=await svc.get_revenue_metrics())


async def get_booking_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[BookingMetrics]:
    return SuccessResponse(data=await svc.get_booking_metrics())


async def get_user_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[UserMetrics]:
    return SuccessResponse(data=await svc.get_user_metrics())


async def get_vendor_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[VendorMetrics]:
    return SuccessResponse(data=await svc.get_vendor_metrics())


async def get_payment_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[PaymentMetrics]:
    return SuccessResponse(data=await svc.get_payment_metrics())


async def get_wallet_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[WalletMetrics]:
    return SuccessResponse(data=await svc.get_wallet_metrics())


async def get_support_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[SupportMetrics]:
    return SuccessResponse(data=await svc.get_support_metrics())


async def get_platform_health(svc: AnalyticsServiceDep) -> SuccessResponse[PlatformHealth]:
    return SuccessResponse(data=await svc.get_platform_health())


async def get_geographic_metrics(svc: AnalyticsServiceDep) -> SuccessResponse[GeographicMetrics]:
    return SuccessResponse(data=await svc.get_geographic_metrics())


async def get_pending_actions(svc: AnalyticsServiceDep) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_pending_actions())


async def get_revenue_chart(
    svc: AnalyticsServiceDep,
    granularity: str = Query(default="day", enum=["day", "week", "month"]),
    days: int = Query(default=30, ge=7, le=365),
) -> SuccessResponse[TimeSeriesChart]:
    try:
        data = await svc.get_revenue_chart(granularity=granularity, days=days)
    except Exception:
        data = TimeSeriesChart(title="Revenue Over Time", granularity=granularity, series=[], date_range={})
    return SuccessResponse(data=data)


async def get_bookings_chart(
    svc: AnalyticsServiceDep,
    granularity: str = Query(default="day", enum=["day", "week", "month"]),
    days: int = Query(default=30, ge=7, le=365),
) -> SuccessResponse[TimeSeriesChart]:
    try:
        data = await svc.get_bookings_chart(granularity=granularity, days=days)
    except Exception:
        data = TimeSeriesChart(title="Bookings Over Time", granularity=granularity, series=[], date_range={})
    return SuccessResponse(data=data)


async def get_users_chart(
    svc: AnalyticsServiceDep,
    granularity: str = Query(default="day", enum=["day", "week", "month"]),
    days: int = Query(default=30, ge=7, le=365),
) -> SuccessResponse[TimeSeriesChart]:
    try:
        data = await svc.get_users_chart(granularity=granularity, days=days)
    except Exception:
        data = TimeSeriesChart(title="New User Registrations", granularity=granularity, series=[], date_range={})
    return SuccessResponse(data=data)


async def get_category_distribution(svc: AnalyticsServiceDep) -> SuccessResponse[PieChartData]:
    try:
        data = await svc.get_category_distribution_chart()
    except Exception:
        data = PieChartData(title="Bookings by Category", segments=[], total=0)
    return SuccessResponse(data=data)


async def get_activity_feed(
    svc: AnalyticsServiceDep,
    limit: int = Query(default=20, ge=5, le=50),
) -> SuccessResponse[ActivityFeed]:
    try:
        data = await svc.get_activity_feed(limit=limit)
    except Exception:
        data = ActivityFeed(items=[], has_more=False)
    return SuccessResponse(data=data)


async def get_dashboard_widgets(svc: AnalyticsServiceDep) -> SuccessResponse[list[DashboardWidget]]:
    try:
        data = await svc.get_dashboard_widgets()
    except Exception:
        data = []
    return SuccessResponse(data=data)
