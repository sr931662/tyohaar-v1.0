"""CMS route package — aggregates all CMS sub-routers under /admin/cms.

SECURITY: every sub-router here (analytics, CRM 360 profiles, bulk vendor/
package actions, import/export, search, automation) handles admin-only data
and admin-only mutations. `dependencies=[Depends(require_admin)]` is applied
once at this aggregate-router level so it's enforced on every route mounted
below, present and future, rather than relying on each controller function
to remember to declare it individually.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.permissions import require_admin

from .analytics_routes import router as analytics_router
from .automation_routes import router as automation_router
from .bulk_routes import router as bulk_router
from .crm_routes import router as crm_router
from .io_routes import router as io_router
from .search_routes import router as search_router

cms_router = APIRouter(prefix="/admin/cms", dependencies=[Depends(require_admin)])

cms_router.include_router(analytics_router)
cms_router.include_router(crm_router)
cms_router.include_router(io_router)
cms_router.include_router(bulk_router)
cms_router.include_router(search_router)
cms_router.include_router(automation_router)

__all__ = ["cms_router"]
