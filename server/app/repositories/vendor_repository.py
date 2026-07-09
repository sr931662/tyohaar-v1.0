"""
Vendor repository — all vendor-domain models.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import VendorStatus, VendorType, VendorVerificationStatus
from app.models.vendors.vendor import Vendor
from app.models.vendors.vendor_availability import VendorBlockedPeriod, VendorWorkSchedule
from app.models.vendors.vendor_bank import VendorBankAccount
from app.models.vendors.vendor_category import VendorCategory
from app.models.vendors.vendor_document import VendorDocument
from app.models.vendors.vendor_gallery import VendorGalleryItem
from app.models.vendors.vendor_profile import VendorProfile
from app.models.vendors.vendor_review import VendorReview
from app.models.vendors.vendor_service import VendorService
from app.models.vendors.vendor_settlement import VendorSettlement
from app.models.vendors.vendor_team import VendorTeamMember
from app.models.vendors.vendor_wallet import VendorWallet
from app.repositories.base import BaseRepository


class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Vendor)

    async def find_by_user(self, user_id: uuid.UUID) -> Vendor | None:
        return await self.find_one(Vendor.user_id == user_id)

    async def find_verified(self, *, skip: int = 0, limit: int = 100) -> list[Vendor]:
        return await self.find_many(
            Vendor.verification_status == VendorVerificationStatus.VERIFIED,
            Vendor.status == VendorStatus.ACTIVE,
            skip=skip,
            limit=limit,
        )

    async def find_by_type(
        self,
        vendor_type: VendorType,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Vendor]:
        return await self.find_many(
            Vendor.vendor_type == vendor_type,
            Vendor.status == VendorStatus.ACTIVE,
            skip=skip,
            limit=limit,
        )

    async def find_pending_verification(self) -> list[Vendor]:
        return await self.find_many(
            Vendor.verification_status == VendorVerificationStatus.PENDING,
        )

    async def find_top_rated(self, limit: int = 20) -> list[Vendor]:
        return await self.find_many(
            Vendor.status == VendorStatus.ACTIVE,
            Vendor.verification_status == VendorVerificationStatus.VERIFIED,
            order_by=Vendor.average_rating.desc(),
            limit=limit,
        )

    async def get_with_profile(self, vendor_id: uuid.UUID) -> Vendor | None:
        return await self.get_by_id(
            vendor_id,
            options=[selectinload(Vendor.profile)],
        )

    async def get_with_services(self, vendor_id: uuid.UUID) -> Vendor | None:
        return await self.get_by_id(
            vendor_id,
            options=[selectinload(Vendor.services)],
        )

    async def update_metrics(
        self,
        vendor_id: uuid.UUID,
        *,
        average_rating: float | None = None,
        review_count: int | None = None,
        completion_count: int | None = None,
        priority_score: float | None = None,
    ) -> None:
        data: dict[str, Any] = {}
        if average_rating is not None:
            data["average_rating"] = average_rating
        if review_count is not None:
            data["review_count"] = review_count
        if completion_count is not None:
            data["completion_count"] = completion_count
        if priority_score is not None:
            data["priority_score"] = priority_score
        if not data:
            return
        stmt = (
            update(Vendor)
            .where(Vendor.id == vendor_id)
            .values(**data)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def increment_completion_count(self, vendor_id: uuid.UUID) -> None:
        stmt = (
            update(Vendor)
            .where(Vendor.id == vendor_id)
            .values(completion_count=Vendor.completion_count + 1)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def count_by_status(self) -> dict[str, int]:
        from sqlalchemy import func
        stmt = (
            select(Vendor.status, func.count().label("count"))
            .where(Vendor.deleted_at.is_(None))
            .group_by(Vendor.status)
        )
        result = await self._session.execute(stmt)
        return {str(row.status): row.count for row in result.all()}


class VendorProfileRepository(BaseRepository[VendorProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorProfile)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> VendorProfile | None:
        return await self.find_one(VendorProfile.vendor_id == vendor_id)


class VendorServiceRepository(BaseRepository[VendorService]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorService)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorService]:
        return await self.find_many(VendorService.vendor_id == vendor_id)

    async def find_active_for_vendor(self, vendor_id: uuid.UUID) -> list[VendorService]:
        return await self.find_many(
            VendorService.vendor_id == vendor_id,
            VendorService.is_active == True,  # noqa: E712
        )


class VendorCategoryRepository(BaseRepository[VendorCategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorCategory)

    async def find_active(self) -> list[VendorCategory]:
        return await self.find_many(VendorCategory.is_active == True)  # noqa: E712

    async def find_by_slug(self, slug: str) -> VendorCategory | None:
        return await self.find_one(VendorCategory.slug == slug)


class VendorDocumentRepository(BaseRepository[VendorDocument]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorDocument)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorDocument]:
        return await self.find_many(VendorDocument.vendor_id == vendor_id)

    async def find_pending_review(self) -> list[VendorDocument]:
        return await self.find_many(VendorDocument.is_verified == False)  # noqa: E712


class VendorBankRepository(BaseRepository[VendorBankAccount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorBankAccount)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorBankAccount]:
        return await self.find_many(VendorBankAccount.vendor_id == vendor_id)

    async def find_primary(self, vendor_id: uuid.UUID) -> VendorBankAccount | None:
        return await self.find_one(
            VendorBankAccount.vendor_id == vendor_id,
            VendorBankAccount.is_primary == True,  # noqa: E712
        )


class VendorAvailabilityRepository(BaseRepository[VendorWorkSchedule]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorWorkSchedule)

    async def find_schedule_for_vendor(self, vendor_id: uuid.UUID) -> list[VendorWorkSchedule]:
        return await self.find_many(VendorWorkSchedule.vendor_id == vendor_id)


class VendorBlockedPeriodRepository(BaseRepository[VendorBlockedPeriod]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorBlockedPeriod)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorBlockedPeriod]:
        return await self.find_many(VendorBlockedPeriod.vendor_id == vendor_id)

    async def find_overlapping(
        self,
        vendor_id: uuid.UUID,
        start: date,
        end: date,
    ) -> list[VendorBlockedPeriod]:
        return await self.find_many(
            VendorBlockedPeriod.vendor_id == vendor_id,
            VendorBlockedPeriod.start_date <= end,
            VendorBlockedPeriod.end_date >= start,
        )


class VendorGalleryRepository(BaseRepository[VendorGalleryItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorGalleryItem)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorGalleryItem]:
        return await self.find_many(
            VendorGalleryItem.vendor_id == vendor_id,
            order_by=VendorGalleryItem.display_order.asc(),
        )


class VendorReviewRepository(BaseRepository[VendorReview]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorReview)

    async def find_by_vendor(
        self,
        vendor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[VendorReview]:
        return await self.find_many(
            VendorReview.vendor_id == vendor_id,
            order_by=VendorReview.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
    ) -> list[VendorReview]:
        return await self.find_many(VendorReview.customer_id == customer_id)


class VendorTeamRepository(BaseRepository[VendorTeamMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorTeamMember)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[VendorTeamMember]:
        return await self.find_many(VendorTeamMember.vendor_id == vendor_id)


class VendorWalletRepository(BaseRepository[VendorWallet]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorWallet)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> VendorWallet | None:
        return await self.find_one(VendorWallet.vendor_id == vendor_id)


class VendorSettlementRepository(BaseRepository[VendorSettlement]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, VendorSettlement)

    async def find_by_vendor(
        self,
        vendor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[VendorSettlement]:
        return await self.find_many(
            VendorSettlement.vendor_id == vendor_id,
            order_by=VendorSettlement.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_pending(self) -> list[VendorSettlement]:
        return await self.find_many(VendorSettlement.status == "pending")


class VendorRepositoryAggregate:
    """Groups all vendor-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.vendors = VendorRepository(session)
        self.profiles = VendorProfileRepository(session)
        self.services = VendorServiceRepository(session)
        self.categories = VendorCategoryRepository(session)
        self.documents = VendorDocumentRepository(session)
        self.bank_accounts = VendorBankRepository(session)
        self.schedules = VendorAvailabilityRepository(session)
        self.blocked_periods = VendorBlockedPeriodRepository(session)
        self.gallery = VendorGalleryRepository(session)
        self.reviews = VendorReviewRepository(session)
        self.team = VendorTeamRepository(session)
        self.wallets = VendorWalletRepository(session)
        self.settlements = VendorSettlementRepository(session)
