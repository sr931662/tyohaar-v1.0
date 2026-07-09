"""
Packages Controller — package CRUD, items, availability, reviews, and categories.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from app.core.current_user import CurrentUserDep, OptionalUserDep
from app.core.dependencies import PackageServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import (
    AdminDep,
    CurrentVendorIdDep,
    CustomerDep,
    resolve_vendor_id_for_user,
)
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.models.enums import UserRole
from app.schemas.base import CursorPage
from app.schemas.packages import (
    PackageAvailabilityCreate,
    PackageAvailabilityResponse,
    PackageAvailabilityUpdate,
    PackageCategoryCreate,
    PackageCategoryResponse,
    PackageCategoryUpdate,
    PackageCreate,
    PackageDetailResponse,
    PackageFilters,
    PackageItemCreate,
    PackageItemResponse,
    PackageItemUpdate,
    PackageResponse,
    PackageReviewCreate,
    PackageReviewResponse,
    PackageUpdate,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def create_package(
    body: PackageCreate,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.create_package(vendor_id=vendor_id, data=body)
    return SuccessResponse(data=result, message="Package created.")


async def get_package(
    package_id: uuid.UUID,
    service: PackageServiceDep,
) -> SuccessResponse[PackageDetailResponse]:
    result = await service.get_package(package_id=package_id)
    return SuccessResponse(data=result, message="Package retrieved.")


async def list_packages(
    filters: Annotated[PackageFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: PackageServiceDep,
    current_user: OptionalUserDep,
) -> CursorPaginatedResponse[PackageResponse]:
    from app.models.enums import UserRole

    is_admin = current_user is not None and current_user.role in (
        UserRole.ADMIN, UserRole.SUPER_ADMIN
    )
    page = await service.list_packages(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size, is_admin=is_admin
    )
    return _cursor_resp(page, pagination.page_size)


async def list_vendor_packages(
    filters: Annotated[PackageFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> CursorPaginatedResponse[PackageResponse]:
    page = await service.list_vendor_packages(
        vendor_id=vendor_id, filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def update_package(
    package_id: uuid.UUID,
    body: PackageUpdate,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.update_package(
        package_id=package_id, vendor_id=vendor_id, data=body
    )
    return SuccessResponse(data=result, message="Package updated.")


async def delete_package(
    package_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[None]:
    await service.delete_package(package_id=package_id, vendor_id=vendor_id)
    return SuccessResponse(data=None, message="Package deleted.")


async def publish_package(
    package_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.publish_package(package_id=package_id, vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Package submitted for review.")


async def approve_package(
    package_id: uuid.UUID,
    _admin: AdminDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.approve_package(package_id=package_id)
    return SuccessResponse(data=result, message="Package approved and published.")


async def reject_package(
    package_id: uuid.UUID,
    _admin: AdminDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.reject_package(package_id=package_id)
    return SuccessResponse(data=result, message="Package rejected and returned to draft.")


async def unpublish_package(
    package_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageResponse]:
    result = await service.unpublish_package(package_id=package_id, vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Package unpublished.")


async def add_item(
    package_id: uuid.UUID,
    body: PackageItemCreate,
    current_user: CurrentUserDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageItemResponse]:
    if current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        result = await service.admin_add_item(package_id=package_id, data=body)
    else:
        vendor_id = await resolve_vendor_id_for_user(current_user)
        result = await service.add_item(
            package_id=package_id, vendor_id=vendor_id, data=body
        )
    return SuccessResponse(data=result, message="Item added.")


async def update_item(
    package_id: uuid.UUID,
    item_id: uuid.UUID,
    body: PackageItemUpdate,
    current_user: CurrentUserDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageItemResponse]:
    if current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        result = await service.admin_update_item(
            package_id=package_id, item_id=item_id, data=body
        )
    else:
        vendor_id = await resolve_vendor_id_for_user(current_user)
        result = await service.update_item(
            package_id=package_id, item_id=item_id, vendor_id=vendor_id, data=body
        )
    return SuccessResponse(data=result, message="Item updated.")


async def delete_item(
    package_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PackageServiceDep,
) -> SuccessResponse[None]:
    if current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        await service.admin_delete_item(package_id=package_id, item_id=item_id)
    else:
        vendor_id = await resolve_vendor_id_for_user(current_user)
        await service.delete_item(
            package_id=package_id, item_id=item_id, vendor_id=vendor_id
        )
    return SuccessResponse(data=None, message="Item deleted.")


async def list_items(
    package_id: uuid.UUID,
    service: PackageServiceDep,
) -> SuccessResponse[list[PackageItemResponse]]:
    items = await service.list_items(package_id=package_id)
    return SuccessResponse(data=items, message="Items retrieved.")


async def set_availability(
    package_id: uuid.UUID,
    body: PackageAvailabilityCreate,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageAvailabilityResponse]:
    result = await service.set_availability(
        package_id=package_id, vendor_id=vendor_id, data=body
    )
    return SuccessResponse(data=result, message="Availability set.")


async def update_availability(
    package_id: uuid.UUID,
    avail_id: uuid.UUID,
    body: PackageAvailabilityUpdate,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageAvailabilityResponse]:
    result = await service.update_availability(
        package_id=package_id, avail_id=avail_id, vendor_id=vendor_id, data=body
    )
    return SuccessResponse(data=result, message="Availability updated.")


async def delete_availability(
    package_id: uuid.UUID,
    avail_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: PackageServiceDep,
) -> SuccessResponse[None]:
    await service.delete_availability(
        package_id=package_id, avail_id=avail_id, vendor_id=vendor_id
    )
    return SuccessResponse(data=None, message="Availability slot deleted.")


async def list_availability(
    package_id: uuid.UUID,
    service: PackageServiceDep,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> SuccessResponse[list[PackageAvailabilityResponse]]:
    slots = await service.list_availability(
        package_id=package_id, date_from=date_from, date_to=date_to
    )
    return SuccessResponse(data=slots, message="Availability retrieved.")


async def add_review(
    package_id: uuid.UUID,
    body: PackageReviewCreate,
    current_user: CustomerDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageReviewResponse]:
    result = await service.add_review(
        package_id=package_id, reviewer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Review submitted.")


async def delete_review(
    package_id: uuid.UUID,
    review_id: uuid.UUID,
    current_user: CustomerDep,
    service: PackageServiceDep,
) -> SuccessResponse[None]:
    await service.delete_review(review_id=review_id, reviewer_id=current_user.id)
    return SuccessResponse(data=None, message="Review deleted.")


async def list_reviews(
    package_id: uuid.UUID,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: PackageServiceDep,
) -> CursorPaginatedResponse[PackageReviewResponse]:
    page = await service.list_reviews(
        package_id=package_id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def list_categories(
    service: PackageServiceDep,
) -> SuccessResponse[list[PackageCategoryResponse]]:
    categories = await service.list_categories()
    return SuccessResponse(data=categories, message="Categories retrieved.")


async def create_category(
    body: PackageCategoryCreate,
    _admin: AdminDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageCategoryResponse]:
    result = await service.create_category(data=body)
    return SuccessResponse(data=result, message="Category created.")


async def update_category(
    cat_id: uuid.UUID,
    body: PackageCategoryUpdate,
    _admin: AdminDep,
    service: PackageServiceDep,
) -> SuccessResponse[PackageCategoryResponse]:
    result = await service.update_category(cat_id=cat_id, data=body)
    return SuccessResponse(data=result, message="Category updated.")


async def delete_category(
    cat_id: uuid.UUID,
    _admin: AdminDep,
    service: PackageServiceDep,
) -> SuccessResponse[None]:
    await service.delete_category(cat_id=cat_id)
    return SuccessResponse(data=None, message="Category deleted.")
