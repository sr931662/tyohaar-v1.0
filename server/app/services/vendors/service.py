"""
VendorService — all vendor-domain business operations.

Layout:
  1. Vendor profile      create / get / update / list
  2. Vendor documents    add / update / delete / list
  3. Vendor gallery      add / delete / list
  4. Vendor availability set / update / delete / get / check
  5. Vendor bank accounts add / update / delete
  6. Vendor reviews      add / update / delete / list
  7. Admin operations    verify / update categories
"""

from __future__ import annotations

from datetime import date, time
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.vendors.vendor import Vendor
from app.models.vendors.vendor_profile import VendorProfile
from app.schemas.base import CursorPage as SchemaCursorPage
from app.schemas.vendors import (
    VendorBankAccountCreate,
    VendorBankAccountUpdate,
    VendorBankAccountResponse,
    VendorCategoryResponse,
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
    VendorSelfResponse,
    VendorUpdate,
)
from app.services.base import BaseService
from app.services.vendors.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.services.vendors.exceptions import (
    VendorAlreadyExistsError,
    VendorDocumentNotFoundError,
    VendorNotFoundError,
    VendorOwnershipError,
)
from app.services.vendors.helpers import calculate_average_rating, sanitize_review_text
from app.services.vendors.validators import (
    validate_bank_account_limit,
    validate_gallery_limit,
    validate_review_not_duplicate,
    validate_vendor_exists,
    validate_vendor_ownership,
)

# ---------------------------------------------------------------------------
# Inline schemas for gallery and availability — not in frozen schema layer v1.0.
# ---------------------------------------------------------------------------
from datetime import datetime

from app.models.enums import DayOfWeek as _DayOfWeek, MediaType as _MediaType
from app.schemas.base import BaseSchema as _BaseSchema


class VendorGalleryCreate(_BaseSchema):
    media_url: str
    media_type: _MediaType = _MediaType.IMAGE
    caption: str | None = None
    sort_order: int = 0
    is_featured: bool = False
    service_id: UUID | None = None


class VendorGalleryUpdate(_BaseSchema):
    media_url: str | None = None
    caption: str | None = None
    sort_order: int | None = None
    is_featured: bool | None = None


class VendorGalleryResponse(_BaseSchema):
    id: UUID
    vendor_id: UUID
    media_url: str
    media_type: str
    caption: str | None = None
    sort_order: int
    is_featured: bool
    created_at: datetime


class VendorAvailabilityCreate(_BaseSchema):
    day_of_week: _DayOfWeek
    is_working: bool = True
    open_time: time | None = None
    close_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    max_bookings_per_day: int = 3


class VendorAvailabilityUpdate(_BaseSchema):
    is_working: bool | None = None
    open_time: time | None = None
    close_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    max_bookings_per_day: int | None = None


class VendorAvailabilityResponse(_BaseSchema):
    id: UUID
    vendor_id: UUID
    day_of_week: str
    is_working: bool
    open_time: time | None = None
    close_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    max_bookings_per_day: int
    created_at: datetime


class VendorDocumentUpdate(_BaseSchema):
    document_url: str | None = None
    expiry_date: date | None = None
    is_primary: bool | None = None


class VendorService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── 1. Vendor Profile ──────────────────────────────────────────────────────

    async def create_vendor(self, user_id: UUID, data: VendorCreate) -> VendorResponse:
        """Register a new vendor. One vendor per user account (ConflictError if exists)."""
        async with self._uow() as uow:
            existing = await uow.vendors.vendors.find_by_user(user_id)
            if existing is not None:
                raise VendorAlreadyExistsError()

            payload = data.model_dump(exclude_unset=True)
            payload["user_id"] = user_id
            vendor = await uow.vendors.vendors.create_from_dict(payload)

            # Create an empty VendorProfile in the same transaction
            await uow.vendors.profiles.create_from_dict({"vendor_id": vendor.id})

            return VendorResponse.model_validate(vendor)

    async def get_vendor(self, vendor_id: UUID) -> VendorResponse:
        async with self._uow() as uow:
            vendor = await validate_vendor_exists(vendor_id, uow)
            return VendorResponse.model_validate(vendor)

    async def get_vendor_by_user(self, user_id: UUID) -> VendorSelfResponse:
        async with self._uow() as uow:
            vendor = await uow.vendors.vendors.find_by_user(user_id)
            if vendor is None:
                raise VendorNotFoundError(str(user_id))
            return VendorSelfResponse.model_validate(vendor)

    async def update_vendor(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: VendorUpdate,
    ) -> VendorSelfResponse:
        async with self._uow() as uow:
            vendor = await validate_vendor_ownership(vendor_id, user_id, uow)
            vendor = await uow.vendors.vendors.update(
                vendor, data.model_dump(exclude_unset=True)
            )
            return VendorSelfResponse.model_validate(vendor)

    async def update_vendor_profile(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: VendorProfileUpdate,
    ) -> VendorProfileResponse:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            profile = await uow.vendors.profiles.find_by_vendor(vendor_id)
            if profile is None:
                profile = await uow.vendors.profiles.create_from_dict(
                    {"vendor_id": vendor_id}
                )
            profile = await uow.vendors.profiles.update(
                profile, data.model_dump(exclude_unset=True)
            )
            return VendorProfileResponse.model_validate(profile)

    async def list_vendors(
        self,
        filters: VendorFilters,
        cursor: str | None,
        limit: int,
    ) -> SchemaCursorPage[VendorResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            repo = uow.vendors.vendors
            filter_args = []
            if hasattr(filters, "vendor_type") and filters.vendor_type is not None:
                filter_args.append(Vendor.vendor_type == filters.vendor_type)
            if hasattr(filters, "status") and filters.status is not None:
                filter_args.append(Vendor.status == filters.status)
            if hasattr(filters, "is_active") and filters.is_active is not None:
                filter_args.append(Vendor.is_active == filters.is_active)
            page = await repo.cursor_paginate(
                *filter_args,
                cursor=cursor,
                limit=limit,
            )
            return SchemaCursorPage(
                items=[VendorResponse.model_validate(v) for v in page.items],
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    # ── 2. Vendor Documents ────────────────────────────────────────────────────

    async def add_document(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: VendorDocumentCreate,
    ) -> VendorDocumentResponse:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["vendor_id"] = vendor_id
            doc = await uow.vendors.documents.create_from_dict(payload)
            return VendorDocumentResponse.model_validate(doc)

    async def update_document(
        self,
        vendor_id: UUID,
        doc_id: UUID,
        user_id: UUID,
        data: object,
    ) -> VendorDocumentResponse:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            doc = await uow.vendors.documents.get_by_id(doc_id)
            if doc is None or doc.vendor_id != vendor_id:
                raise VendorDocumentNotFoundError(str(doc_id))
            doc = await uow.vendors.documents.update(
                doc, data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return VendorDocumentResponse.model_validate(doc)

    async def delete_document(
        self,
        vendor_id: UUID,
        doc_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            doc = await uow.vendors.documents.get_by_id(doc_id)
            if doc is None or doc.vendor_id != vendor_id:
                raise VendorDocumentNotFoundError(str(doc_id))
            await uow.vendors.documents.delete(doc)

    async def list_documents(self, vendor_id: UUID) -> list[VendorDocumentResponse]:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            docs = await uow.vendors.documents.find_by_vendor(vendor_id)
            return [VendorDocumentResponse.model_validate(d) for d in docs]

    # ── 3. Vendor Gallery ──────────────────────────────────────────────────────

    async def add_gallery_item(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            await validate_gallery_limit(vendor_id, uow)
            payload = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            payload["vendor_id"] = vendor_id
            item = await uow.vendors.gallery.create_from_dict(payload)
            return VendorGalleryResponse.model_validate(item)  # type: ignore[call-arg]

    async def delete_gallery_item(
        self,
        vendor_id: UUID,
        item_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            item = await uow.vendors.gallery.get_by_id(item_id)
            if item is None or item.vendor_id != vendor_id:
                raise VendorNotFoundError(f"gallery item {item_id}")
            await uow.vendors.gallery.delete(item)

    async def list_gallery(self, vendor_id: UUID) -> list[object]:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            items = await uow.vendors.gallery.find_by_vendor(vendor_id)
            return [VendorGalleryResponse.model_validate(i) for i in items]  # type: ignore[call-arg]

    # ── 4. Vendor Availability ─────────────────────────────────────────────────

    async def set_availability(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            payload = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            payload["vendor_id"] = vendor_id
            slot = await uow.vendors.schedules.create_from_dict(payload)
            return VendorAvailabilityResponse.model_validate(slot)  # type: ignore[call-arg]

    async def update_availability(
        self,
        vendor_id: UUID,
        slot_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            slot = await uow.vendors.schedules.get_by_id(slot_id)
            if slot is None or slot.vendor_id != vendor_id:
                raise VendorNotFoundError(f"availability slot {slot_id}")
            slot = await uow.vendors.schedules.update(
                slot, data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return VendorAvailabilityResponse.model_validate(slot)  # type: ignore[call-arg]

    async def delete_availability(
        self,
        vendor_id: UUID,
        slot_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            slot = await uow.vendors.schedules.get_by_id(slot_id)
            if slot is None or slot.vendor_id != vendor_id:
                raise VendorNotFoundError(f"availability slot {slot_id}")
            await uow.vendors.schedules.delete(slot)

    async def get_availability(
        self,
        vendor_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[object]:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            slots = await uow.vendors.schedules.find_schedule_for_vendor(vendor_id)
            return [VendorAvailabilityResponse.model_validate(s) for s in slots]  # type: ignore[call-arg]

    async def check_availability(
        self,
        vendor_id: UUID,
        event_date: date,
        start_time: time,
        end_time: time,
    ) -> bool:
        """Check whether vendor is available on *event_date* from *start_time* to *end_time*."""
        from app.services.vendors.helpers import is_vendor_available

        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)

            # Check blocked periods first
            blocked = await uow.vendors.blocked_periods.find_overlapping(
                vendor_id, event_date, event_date
            )
            if blocked:
                return False

            # Check work schedule
            schedule = await uow.vendors.schedules.find_schedule_for_vendor(vendor_id)
            return is_vendor_available(schedule, event_date, start_time, end_time)

    # ── 5. Vendor Bank Accounts ────────────────────────────────────────────────

    async def list_bank_accounts(self, vendor_id: UUID) -> list[VendorBankAccountResponse]:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            accounts = await uow.vendors.bank_accounts.find_by_vendor(vendor_id)
            return [VendorBankAccountResponse.model_validate(a) for a in accounts]

    async def add_bank_account(
        self,
        vendor_id: UUID,
        user_id: UUID,
        data: VendorBankAccountCreate,
    ) -> VendorBankAccountResponse:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            await validate_bank_account_limit(vendor_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["vendor_id"] = vendor_id
            account = await uow.vendors.bank_accounts.create_from_dict(payload)
            return VendorBankAccountResponse.model_validate(account)

    async def update_bank_account(
        self,
        vendor_id: UUID,
        bank_id: UUID,
        user_id: UUID,
        data: VendorBankAccountUpdate,
    ) -> VendorBankAccountResponse:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            account = await uow.vendors.bank_accounts.get_by_id(bank_id)
            if account is None or account.vendor_id != vendor_id:
                raise VendorNotFoundError(f"bank account {bank_id}")
            account = await uow.vendors.bank_accounts.update(
                account, data.model_dump(exclude_unset=True)
            )
            return VendorBankAccountResponse.model_validate(account)

    async def delete_bank_account(
        self,
        vendor_id: UUID,
        bank_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_vendor_ownership(vendor_id, user_id, uow)
            account = await uow.vendors.bank_accounts.get_by_id(bank_id)
            if account is None or account.vendor_id != vendor_id:
                raise VendorNotFoundError(f"bank account {bank_id}")
            await uow.vendors.bank_accounts.delete(account)

    # ── 6. Vendor Reviews ──────────────────────────────────────────────────────

    async def add_review(
        self,
        vendor_id: UUID,
        reviewer_id: UUID,
        data: VendorReviewCreate,
    ) -> VendorReviewResponse:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            await validate_review_not_duplicate(vendor_id, reviewer_id, uow)

            body = data.body
            if body:
                body = sanitize_review_text(body)

            payload = data.model_dump(exclude_unset=True)
            payload["vendor_id"] = vendor_id
            payload["customer_id"] = reviewer_id
            if body is not None:
                payload["body"] = body

            review = await uow.vendors.reviews.create_from_dict(payload)
            result = VendorReviewResponse.model_validate(review)

        # Side effect: recalculate avg_rating AFTER the transaction closes
        await self._recalculate_vendor_rating(vendor_id)

        return result

    async def update_review(
        self,
        review_id: UUID,
        reviewer_id: UUID,
        data: VendorReviewUpdate,
    ) -> VendorReviewResponse:
        async with self._uow() as uow:
            review = await uow.vendors.reviews.get_by_id(review_id)
            if review is None:
                raise VendorNotFoundError(f"review {review_id}")
            if review.customer_id != reviewer_id:
                raise VendorOwnershipError()

            update_data = data.model_dump(exclude_unset=True)
            if "body" in update_data and update_data["body"]:
                update_data["body"] = sanitize_review_text(update_data["body"])

            review = await uow.vendors.reviews.update(review, update_data)
            return VendorReviewResponse.model_validate(review)

    async def delete_review(
        self,
        review_id: UUID,
        reviewer_id: UUID,
    ) -> None:
        vendor_id: UUID | None = None
        async with self._uow() as uow:
            review = await uow.vendors.reviews.get_by_id(review_id)
            if review is None:
                raise VendorNotFoundError(f"review {review_id}")
            if review.customer_id != reviewer_id:
                raise VendorOwnershipError()
            vendor_id = review.vendor_id
            await uow.vendors.reviews.delete(review)

        # Side effect: recalculate avg_rating after deletion
        if vendor_id is not None:
            await self._recalculate_vendor_rating(vendor_id)

    async def list_reviews(
        self,
        vendor_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> SchemaCursorPage[VendorReviewResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            from app.models.vendors.vendor_review import VendorReview

            page = await uow.vendors.reviews.cursor_paginate(
                VendorReview.vendor_id == vendor_id,
                cursor=cursor,
                limit=limit,
            )
            return SchemaCursorPage(
                items=[VendorReviewResponse.model_validate(r) for r in page.items],
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    # ── 7. Admin Operations ────────────────────────────────────────────────────

    async def verify_vendor(
        self,
        vendor_id: UUID,
        admin_id: UUID,
        approved: bool,
        notes: str | None = None,
    ) -> VendorResponse:
        from app.models.enums import VendorStatus, VendorVerificationStatus

        async with self._uow() as uow:
            vendor = await validate_vendor_exists(vendor_id, uow)

            new_verification_status = (
                VendorVerificationStatus.VERIFIED
                if approved
                else VendorVerificationStatus.REJECTED
            )
            new_status = VendorStatus.ACTIVE if approved else VendorStatus.SUSPENDED

            update_data: dict = {
                "verification_status": new_verification_status,
                "status": new_status,
                "is_active": approved,
            }
            vendor = await uow.vendors.vendors.update(vendor, update_data)
            return VendorResponse.model_validate(vendor)

    async def update_vendor_categories(
        self,
        vendor_id: UUID,
        category_ids: list[UUID],
    ) -> list[VendorCategoryResponse]:
        async with self._uow() as uow:
            await validate_vendor_exists(vendor_id, uow)
            categories = await uow.vendors.categories.get_by_ids(category_ids)
            # The association is managed via vendor_service category FK in VendorService;
            # here we return the resolved category objects for confirmation.
            return [VendorCategoryResponse.model_validate(c) for c in categories]

    async def delete_vendor_cascade(self, vendor_id: UUID) -> int:
        """
        Admin-only cleanup: soft-delete a vendor and every package they
        created. Soft (not hard) delete — reversible, and avoids violating
        FK constraints from existing bookings/payments/reviews that
        reference this vendor. Returns the number of packages removed.
        """
        from app.models.packages.package import Package

        async with self._uow() as uow:
            vendor = await validate_vendor_exists(vendor_id, uow)

            packages = await uow.packages.packages.find_many(Package.vendor_id == vendor_id)
            for package in packages:
                await uow.packages.packages.soft_delete(package)

            await uow.vendors.vendors.soft_delete(vendor)
            return len(packages)

    # ── Internal Helpers ───────────────────────────────────────────────────────

    async def _recalculate_vendor_rating(self, vendor_id: UUID) -> None:
        """Fetch all published reviews and update denormalized average_rating."""
        async with self._uow() as uow:
            from app.models.vendors.vendor_review import VendorReview, ReviewModerationStatus

            reviews = await uow.vendors.reviews.find_many(
                VendorReview.vendor_id == vendor_id,
                VendorReview.moderation_status == ReviewModerationStatus.APPROVED,
                VendorReview.is_published == True,  # noqa: E712
            )
            ratings = [r.rating for r in reviews]
            avg = calculate_average_rating(ratings)

            vendor = await uow.vendors.vendors.get_by_id(vendor_id)
            if vendor is not None:
                await uow.vendors.vendors.update(
                    vendor,
                    {"average_rating": avg, "review_count": len(ratings)},
                )
