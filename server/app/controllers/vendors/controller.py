"""
Vendors Controller — vendor profile, documents, gallery, availability, bank accounts, and reviews.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Annotated

from fastapi import Depends, Query

from app.core.current_user import CurrentUserDep
from app.core.dependencies import VendorServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep, CustomerDep, VendorDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.vendors import (
    VendorBankAccountCreate,
    VendorBankAccountUpdate,
    VendorBankAccountResponse,
    VendorCreate,
    VendorDocumentCreate,
    VendorDocumentResponse,
    VendorFilters,
    VendorProfileResponse,
    VendorProfileUpdate,
    VendorResponse,
    VendorReviewCreate,
    VendorReviewResponse,
    VendorReviewUpdate,
)
from app.services.vendors.service import (
    VendorAvailabilityCreate,
    VendorAvailabilityResponse,
    VendorAvailabilityUpdate,
    VendorDocumentUpdate,
    VendorGalleryCreate,
    VendorGalleryResponse,
)


def _cursor_resp(
    page: CursorPage,
    page_size: int,
) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(
            cursor=page.next_cursor,
            has_next=page.has_more,
            page_size=page_size,
        ),
    )


async def create_vendor(
    body: VendorCreate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorResponse]:
    result = await service.create_vendor(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Vendor created.")


async def get_vendor(
    vendor_id: uuid.UUID,
    service: VendorServiceDep,
) -> SuccessResponse[VendorResponse]:
    result = await service.get_vendor(vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Vendor retrieved.")


async def get_my_vendor(
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorResponse]:
    result = await service.get_vendor_by_user(user_id=current_user.id)
    return SuccessResponse(data=result, message="Vendor profile retrieved.")


async def update_vendor_profile(
    vendor_id: uuid.UUID,
    body: VendorProfileUpdate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorProfileResponse]:
    result = await service.update_vendor_profile(
        vendor_id=vendor_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Vendor profile updated.")


async def list_vendors(
    filters: Annotated[VendorFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: VendorServiceDep,
) -> CursorPaginatedResponse[VendorResponse]:
    page = await service.list_vendors(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def add_document(
    vendor_id: uuid.UUID,
    body: VendorDocumentCreate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorDocumentResponse]:
    result = await service.add_document(
        vendor_id=vendor_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Document added.")


async def update_document(
    vendor_id: uuid.UUID,
    doc_id: uuid.UUID,
    body: VendorDocumentUpdate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorDocumentResponse]:
    result = await service.update_document(
        vendor_id=vendor_id, doc_id=doc_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Document updated.")


async def delete_document(
    vendor_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[None]:
    await service.delete_document(
        vendor_id=vendor_id, doc_id=doc_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Document deleted.")


async def list_documents(
    vendor_id: uuid.UUID,
    service: VendorServiceDep,
) -> SuccessResponse[list[VendorDocumentResponse]]:
    docs = await service.list_documents(vendor_id=vendor_id)
    return SuccessResponse(data=docs, message="Documents retrieved.")


async def add_gallery_item(
    vendor_id: uuid.UUID,
    body: VendorGalleryCreate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorGalleryResponse]:
    result = await service.add_gallery_item(
        vendor_id=vendor_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Gallery item added.")


async def delete_gallery_item(
    vendor_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[None]:
    await service.delete_gallery_item(
        vendor_id=vendor_id, item_id=item_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Gallery item deleted.")


async def list_gallery(
    vendor_id: uuid.UUID,
    service: VendorServiceDep,
) -> SuccessResponse[list[VendorGalleryResponse]]:
    items = await service.list_gallery(vendor_id=vendor_id)
    return SuccessResponse(data=items, message="Gallery retrieved.")


async def set_availability(
    vendor_id: uuid.UUID,
    body: VendorAvailabilityCreate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorAvailabilityResponse]:
    result = await service.set_availability(
        vendor_id=vendor_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Availability set.")


async def update_availability(
    vendor_id: uuid.UUID,
    slot_id: uuid.UUID,
    body: VendorAvailabilityUpdate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorAvailabilityResponse]:
    result = await service.update_availability(
        vendor_id=vendor_id, slot_id=slot_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Availability updated.")


async def delete_availability(
    vendor_id: uuid.UUID,
    slot_id: uuid.UUID,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[None]:
    await service.delete_availability(
        vendor_id=vendor_id, slot_id=slot_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Availability slot deleted.")


async def get_availability(
    vendor_id: uuid.UUID,
    service: VendorServiceDep,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> SuccessResponse[list[VendorAvailabilityResponse]]:
    slots = await service.get_availability(
        vendor_id=vendor_id, date_from=date_from, date_to=date_to
    )
    return SuccessResponse(data=slots, message="Availability retrieved.")


async def check_availability(
    vendor_id: uuid.UUID,
    service: VendorServiceDep,
    event_date: date = Query(...),
    start_time: time = Query(...),
    end_time: time = Query(...),
) -> SuccessResponse[bool]:
    available = await service.check_availability(
        vendor_id=vendor_id,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
    )
    return SuccessResponse(data=available, message="Availability checked.")


async def list_bank_accounts(
    vendor_id: uuid.UUID,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[list[VendorBankAccountResponse]]:
    result = await service.list_bank_accounts(vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Bank accounts retrieved.")


async def add_bank_account(
    vendor_id: uuid.UUID,
    body: VendorBankAccountCreate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorBankAccountResponse]:
    result = await service.add_bank_account(
        vendor_id=vendor_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Bank account added.")


async def update_bank_account(
    vendor_id: uuid.UUID,
    bank_id: uuid.UUID,
    body: VendorBankAccountUpdate,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorBankAccountResponse]:
    result = await service.update_bank_account(
        vendor_id=vendor_id, bank_id=bank_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Bank account updated.")


async def delete_bank_account(
    vendor_id: uuid.UUID,
    bank_id: uuid.UUID,
    current_user: VendorDep,
    service: VendorServiceDep,
) -> SuccessResponse[None]:
    await service.delete_bank_account(
        vendor_id=vendor_id, bank_id=bank_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Bank account deleted.")


async def add_review(
    vendor_id: uuid.UUID,
    body: VendorReviewCreate,
    current_user: CustomerDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorReviewResponse]:
    result = await service.add_review(
        vendor_id=vendor_id, reviewer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Review submitted.")


async def update_review(
    vendor_id: uuid.UUID,
    review_id: uuid.UUID,
    body: VendorReviewUpdate,
    current_user: CustomerDep,
    service: VendorServiceDep,
) -> SuccessResponse[VendorReviewResponse]:
    result = await service.update_review(
        review_id=review_id, reviewer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Review updated.")


async def delete_review(
    vendor_id: uuid.UUID,
    review_id: uuid.UUID,
    current_user: CustomerDep,
    service: VendorServiceDep,
) -> SuccessResponse[None]:
    await service.delete_review(review_id=review_id, reviewer_id=current_user.id)
    return SuccessResponse(data=None, message="Review deleted.")


async def list_reviews(
    vendor_id: uuid.UUID,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: VendorServiceDep,
) -> CursorPaginatedResponse[VendorReviewResponse]:
    page = await service.list_reviews(
        vendor_id=vendor_id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def verify_vendor(
    vendor_id: uuid.UUID,
    current_user: AdminDep,
    service: VendorServiceDep,
    approved: bool = Query(...),
    notes: str | None = Query(default=None),
) -> SuccessResponse[VendorResponse]:
    result = await service.verify_vendor(
        vendor_id=vendor_id, admin_id=current_user.id, approved=approved, notes=notes
    )
    return SuccessResponse(data=result, message="Vendor verification processed.")


async def update_vendor_categories(
    vendor_id: uuid.UUID,
    category_ids: list[uuid.UUID],
    _admin: AdminDep,
    service: VendorServiceDep,
) -> SuccessResponse[list]:
    result = await service.update_vendor_categories(
        vendor_id=vendor_id, category_ids=category_ids
    )
    return SuccessResponse(data=result, message="Vendor categories updated.")
