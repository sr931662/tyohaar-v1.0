"""
Route Layer v1.0 — aggregates all domain APIRouter instances.

Usage in application factory (main.py):

    from app.routes import all_routers

    for router in all_routers:
        app.include_router(router, prefix="/api/v1")
"""

from __future__ import annotations

from app.routes.admin.routes import router as admin_router
from app.routes.auth.routes import router as auth_router
from app.routes.cms import cms_router
from app.routes.bookings.routes import router as bookings_router
from app.routes.budgets.routes import router as budgets_router
from app.routes.common.routes import router as common_router
from app.routes.media.routes import router as media_router
from app.routes.memberships.routes import router as memberships_router
from app.routes.notifications.routes import router as notifications_router
from app.routes.occasions.routes import router as occasions_router
from app.routes.packages.routes import router as packages_router
from app.routes.payments.routes import router as payments_router
from app.routes.referrals.routes import router as referrals_router
from app.routes.support.routes import router as support_router
from app.routes.users.routes import router as users_router
from app.routes.vendors.routes import router as vendors_router
from app.routes.wallets.routes import router as wallets_router

all_routers = [
    auth_router,
    users_router,
    vendors_router,
    occasions_router,
    packages_router,
    bookings_router,
    payments_router,
    wallets_router,
    memberships_router,
    notifications_router,
    support_router,
    media_router,
    referrals_router,
    budgets_router,
    admin_router,
    common_router,
    cms_router,
]

__all__ = [
    "all_routers",
    "auth_router",
    "users_router",
    "vendors_router",
    "occasions_router",
    "packages_router",
    "bookings_router",
    "payments_router",
    "wallets_router",
    "memberships_router",
    "notifications_router",
    "support_router",
    "media_router",
    "referrals_router",
    "budgets_router",
    "admin_router",
    "common_router",
    "cms_router",
]
