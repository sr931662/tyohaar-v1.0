"""Global Search CMS controller functions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from app.core.responses import SuccessResponse
from app.schemas.cms.search import GlobalSearchRequest, GlobalSearchResponse
from app.services.cms.search_service import SearchService


def get_search_service() -> SearchService:
    return SearchService()


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


async def global_search(
    svc: SearchServiceDep,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    entity_types: list[str] | None = Query(
        default=None,
        description="Limit to specific entity types (users, vendors, packages, …)",
    ),
    limit_per_type: int = Query(default=5, ge=1, le=20),
) -> SuccessResponse[GlobalSearchResponse]:
    request = GlobalSearchRequest(
        q=q,
        entity_types=entity_types,
        limit_per_type=limit_per_type,
    )
    result = await svc.global_search(request)
    return SuccessResponse(data=result, message=f"Search completed in {result.took_ms}ms")
