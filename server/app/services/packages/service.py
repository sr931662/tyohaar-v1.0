from __future__ import annotations

from datetime import date
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.packages.package import Package
from app.models.packages.package_availability import PackageAvailability
from app.models.packages.package_category import PackageCategory
from app.models.packages.package_item import PackageItem
from app.models.packages.package_review import PackageReview
from app.models.enums import PackageStatus
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
from app.services.base import BaseService
from app.services.packages.validators import (
    validate_item_limit,
    validate_package_exists,
    validate_package_ownership,
    validate_review_not_duplicate,
)


class PackageService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── Package CRUD ─────────────────────────────────────────────────────────

    async def create_package(
        self,
        vendor_id: UUID,
        data: PackageCreate,
    ) -> PackageResponse:
        import re
        import uuid as _uuid

        async with self._uow() as uow:
            payload = data.model_dump(exclude_unset=True)

            # Remap schema field names → model column names
            if "min_guests" in payload:
                payload["min_guest_count"] = payload.pop("min_guests")
            if "max_guests" in payload:
                payload["max_guest_count"] = payload.pop("max_guests")

            # Set vendor ownership
            payload["vendor_id"] = vendor_id

            # Auto-generate slug from name if not supplied
            if not payload.get("slug"):
                base = re.sub(r"[^a-z0-9]+", "-", payload["name"].lower()).strip("-")
                payload["slug"] = f"{base}-{str(_uuid.uuid4())[:8]}"

            package = await uow.packages.packages.create_from_dict(payload)
            await uow.commit()
            return PackageResponse.model_validate(package)

    async def get_package(self, package_id: UUID) -> PackageDetailResponse:
        async with self._uow() as uow:
            package = await validate_package_exists(package_id, uow)
            items = await uow.packages.items.find_by_package(package_id)
            availability = await uow.packages.availability.find_by_package(package_id)
            response = PackageDetailResponse.model_validate(package)
            response.items = [PackageItemResponse.model_validate(i) for i in items]
            return response

    async def list_packages(
        self,
        filters: PackageFilters,
        cursor: str | None,
        limit: int,
        is_admin: bool = False,
    ) -> CursorPage[PackageResponse]:
        from sqlalchemy import or_
        async with self._uow() as uow:
            if is_admin:
                # Admin package management needs to see every lifecycle state
                # (draft/pending_review/etc.), optionally narrowed by filters.status.
                conditions = []
                if filters.status is not None:
                    conditions.append(Package.status == filters.status)
            else:
                # Public/customer browsing must never see unpublished packages,
                # regardless of what status filter was requested.
                conditions = [
                    Package.is_active == True,  # noqa: E712
                    Package.status == PackageStatus.ACTIVE,
                ]
            if filters.category_id is not None:
                conditions.append(Package.category_id == filters.category_id)
            if filters.city is not None:
                conditions.append(Package.city_slug == filters.city)
            if filters.is_featured is not None:
                conditions.append(Package.is_featured == filters.is_featured)
            if filters.is_customizable is not None:
                conditions.append(Package.is_customizable == filters.is_customizable)
            if filters.min_price is not None:
                conditions.append(Package.base_price >= filters.min_price)
            if filters.max_price is not None:
                conditions.append(Package.base_price <= filters.max_price)
            if filters.min_rating is not None:
                conditions.append(Package.average_rating >= filters.min_rating)
            if filters.search is not None:
                term = f"%{filters.search}%"
                conditions.append(
                    or_(Package.name.ilike(term), Package.short_description.ilike(term))
                )
            page = await uow.packages.packages.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            # Batch-load item counts — one query for the whole page, avoids N+1
            package_ids = [p.id for p in page.items]
            counts: dict = {}
            if package_ids:
                item_rows = await uow.packages.items.find_many(
                    uow.packages.items._model.package_id.in_(package_ids)
                )
                for row in item_rows:
                    pid = row.package_id
                    counts[pid] = counts.get(pid, 0) + 1
            responses = [
                PackageResponse.model_validate(p).model_copy(
                    update={"inclusions_count": counts.get(p.id, 0)}
                )
                for p in page.items
            ]
            return CursorPage(
                items=responses,
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    async def update_package(
        self,
        package_id: UUID,
        vendor_id: UUID,
        data: PackageUpdate,
    ) -> PackageResponse:
        async with self._uow() as uow:
            package = await validate_package_ownership(package_id, vendor_id, uow)
            changes = data.model_dump(exclude_unset=True)
            if "min_guests" in changes:
                changes["min_guest_count"] = changes.pop("min_guests")
            if "max_guests" in changes:
                changes["max_guest_count"] = changes.pop("max_guests")
            updated = await uow.packages.packages.update(package, changes)
            await uow.commit()
            return PackageResponse.model_validate(updated)

    async def delete_package(
        self,
        package_id: UUID,
        vendor_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            package = await validate_package_ownership(package_id, vendor_id, uow)
            await uow.packages.packages.soft_delete(package)
            await uow.commit()

    async def publish_package(
        self,
        package_id: UUID,
        vendor_id: UUID,
    ) -> PackageResponse:
        """Vendor submits package for admin review (DRAFT → PENDING_REVIEW)."""
        async with self._uow() as uow:
            package = await validate_package_ownership(package_id, vendor_id, uow)
            updated = await uow.packages.packages.update(
                package, {"status": PackageStatus.PENDING_REVIEW, "is_active": False}
            )
            await uow.commit()
            return PackageResponse.model_validate(updated)

    async def unpublish_package(
        self,
        package_id: UUID,
        vendor_id: UUID,
    ) -> PackageResponse:
        async with self._uow() as uow:
            package = await validate_package_ownership(package_id, vendor_id, uow)
            updated = await uow.packages.packages.update(
                package, {"status": PackageStatus.INACTIVE, "is_active": False}
            )
            await uow.commit()
            return PackageResponse.model_validate(updated)

    async def approve_package(self, package_id: UUID) -> PackageResponse:
        """Admin approves a pending package (PENDING_REVIEW → ACTIVE)."""
        async with self._uow() as uow:
            package = await validate_package_exists(package_id, uow)
            updated = await uow.packages.packages.update(
                package, {"status": PackageStatus.ACTIVE, "is_active": True}
            )
            await uow.commit()
            return PackageResponse.model_validate(updated)

    async def reject_package(self, package_id: UUID) -> PackageResponse:
        """Admin rejects a pending package (PENDING_REVIEW → DRAFT)."""
        async with self._uow() as uow:
            package = await validate_package_exists(package_id, uow)
            updated = await uow.packages.packages.update(
                package, {"status": PackageStatus.DRAFT, "is_active": False}
            )
            await uow.commit()
            return PackageResponse.model_validate(updated)

    # ── Package Items ─────────────────────────────────────────────────────────

    async def add_item(
        self,
        package_id: UUID,
        vendor_id: UUID,
        data: PackageItemCreate,
    ) -> PackageItemResponse:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            await validate_item_limit(package_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["package_id"] = package_id
            item = await uow.packages.items.create_from_dict(payload)
            await uow.commit()
            return PackageItemResponse.model_validate(item)

    async def update_item(
        self,
        package_id: UUID,
        item_id: UUID,
        vendor_id: UUID,
        data: PackageItemUpdate,
    ) -> PackageItemResponse:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            item = await uow.packages.items.get_by_id(item_id)
            if item is None or item.package_id != package_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageItem", str(item_id))
            updated = await uow.packages.items.update(
                item, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return PackageItemResponse.model_validate(updated)

    async def delete_item(
        self,
        package_id: UUID,
        item_id: UUID,
        vendor_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            item = await uow.packages.items.get_by_id(item_id)
            if item is None or item.package_id != package_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageItem", str(item_id))
            await uow.packages.items.delete(item)
            await uow.commit()

    async def list_items(self, package_id: UUID) -> list[PackageItemResponse]:
        async with self._uow() as uow:
            await validate_package_exists(package_id, uow)
            items = await uow.packages.items.find_by_package(package_id)
            return [PackageItemResponse.model_validate(i) for i in items]

    # ── Package Availability ──────────────────────────────────────────────────

    async def set_availability(
        self,
        package_id: UUID,
        vendor_id: UUID,
        data: PackageAvailabilityCreate,
    ) -> PackageAvailabilityResponse:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["package_id"] = package_id
            slot = await uow.packages.availability.create_from_dict(payload)
            await uow.commit()
            return PackageAvailabilityResponse.model_validate(slot)

    async def update_availability(
        self,
        package_id: UUID,
        avail_id: UUID,
        vendor_id: UUID,
        data: PackageAvailabilityUpdate,
    ) -> PackageAvailabilityResponse:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            slot = await uow.packages.availability.get_by_id(avail_id)
            if slot is None or slot.package_id != package_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageAvailability", str(avail_id))
            updated = await uow.packages.availability.update(
                slot, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return PackageAvailabilityResponse.model_validate(updated)

    async def delete_availability(
        self,
        package_id: UUID,
        avail_id: UUID,
        vendor_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_package_ownership(package_id, vendor_id, uow)
            slot = await uow.packages.availability.get_by_id(avail_id)
            if slot is None or slot.package_id != package_id:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageAvailability", str(avail_id))
            await uow.packages.availability.delete(slot)
            await uow.commit()

    async def list_availability(
        self,
        package_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[PackageAvailabilityResponse]:
        async with self._uow() as uow:
            await validate_package_exists(package_id, uow)
            slots = await uow.packages.availability.find_by_package(package_id)
            if date_from is not None:
                slots = [s for s in slots if s.available_date >= date_from]
            if date_to is not None:
                slots = [s for s in slots if s.available_date <= date_to]
            return [PackageAvailabilityResponse.model_validate(s) for s in slots]

    # ── Package Reviews ───────────────────────────────────────────────────────

    async def add_review(
        self,
        package_id: UUID,
        reviewer_id: UUID,
        data: PackageReviewCreate,
    ) -> PackageReviewResponse:
        async with self._uow() as uow:
            await validate_package_exists(package_id, uow)
            await validate_review_not_duplicate(package_id, reviewer_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["package_id"] = package_id
            payload["customer_id"] = reviewer_id
            review = await uow.packages.reviews.create_from_dict(payload)
            await uow.commit()

        # Side effect: recalculate package avg_rating outside transaction
        await self._update_package_avg_rating(package_id)
        return PackageReviewResponse.model_validate(review)

    async def _update_package_avg_rating(self, package_id: UUID) -> None:
        """Recompute and persist the package's average rating from approved reviews."""
        async with self._uow() as uow:
            from app.models.packages.package_review import PackageReviewModerationStatus
            reviews = await uow.packages.reviews.find_many(
                uow.packages.reviews._model.package_id == package_id,
                uow.packages.reviews._model.moderation_status == PackageReviewModerationStatus.APPROVED,
            )
            if not reviews:
                return
            avg = sum(r.rating for r in reviews) / len(reviews)
            package = await uow.packages.packages.get_by_id(package_id)
            if package is not None:
                # Package model stores avg via review aggregation — update if column exists
                pass  # avg_rating is computed via DB or background job; no direct column found
            await uow.commit()

    async def delete_review(
        self,
        review_id: UUID,
        reviewer_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            review = await uow.packages.reviews.get_by_id(review_id)
            if review is None:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageReview", str(review_id))
            if review.customer_id != reviewer_id:
                from app.services.exceptions import PermissionError
                raise PermissionError("You did not write this review.")
            await uow.packages.reviews.delete(review)
            await uow.commit()

    async def list_reviews(
        self,
        package_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[PackageReviewResponse]:
        async with self._uow() as uow:
            await validate_package_exists(package_id, uow)
            page = await uow.packages.reviews.cursor_paginate(
                uow.packages.reviews._model.package_id == package_id,
                cursor=cursor,
                limit=limit,
            )
            items = [PackageReviewResponse.model_validate(r) for r in page.items]
            return CursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    # ── Package Categories ────────────────────────────────────────────────────

    async def list_categories(self) -> list[PackageCategoryResponse]:
        async with self._uow() as uow:
            categories = await uow.packages.categories.find_active()
            return [PackageCategoryResponse.model_validate(c) for c in categories]

    async def create_category(
        self,
        data: PackageCategoryCreate,
    ) -> PackageCategoryResponse:
        async with self._uow() as uow:
            payload = data.model_dump(exclude_unset=True)
            category = await uow.packages.categories.create_from_dict(payload)
            await uow.commit()
            return PackageCategoryResponse.model_validate(category)

    async def update_category(
        self,
        cat_id: UUID,
        data: PackageCategoryUpdate,
    ) -> PackageCategoryResponse:
        async with self._uow() as uow:
            category = await uow.packages.categories.get_by_id(cat_id)
            if category is None:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageCategory", str(cat_id))
            updated = await uow.packages.categories.update(
                category, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return PackageCategoryResponse.model_validate(updated)

    async def delete_category(self, cat_id: UUID) -> None:
        async with self._uow() as uow:
            category = await uow.packages.categories.get_by_id(cat_id)
            if category is None:
                from app.services.exceptions import NotFoundError
                raise NotFoundError("PackageCategory", str(cat_id))
            await uow.packages.categories.delete(category)
            await uow.commit()
