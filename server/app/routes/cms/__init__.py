"""CMS route package — aggregates all CMS sub-routers under /admin/cms."""

from __future__ import annotations

from fastapi import APIRouter

from .analytics_routes import router as analytics_router
from .automation_routes import router as automation_router
from .bulk_routes import router as bulk_router
from .crm_routes import router as crm_router
from .io_routes import router as io_router
from .search_routes import router as search_router

cms_router = APIRouter(prefix="/admin/cms")

cms_router.include_router(analytics_router)
cms_router.include_router(crm_router)
cms_router.include_router(io_router)
cms_router.include_router(bulk_router)
cms_router.include_router(search_router)
cms_router.include_router(automation_router)

__all__ = ["cms_router"]
