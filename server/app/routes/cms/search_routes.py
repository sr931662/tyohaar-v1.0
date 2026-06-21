"""Global Search endpoints — /admin/cms/search/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.search_controller import global_search

router = APIRouter(prefix="/search", tags=["CMS — Global Search"])

router.add_api_route(
    "/",
    global_search,
    methods=["GET"],
    summary="Global search across users, vendors, packages, bookings, tickets, categories, occasions",
)
