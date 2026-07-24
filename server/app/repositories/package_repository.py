"""
Package repository — Package and all child models.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.packages.package import Package
from app.models.packages.package_addon import PackageAddon
from app.models.packages.package_availability import PackageAvailability
from app.models.packages.package_category import PackageCategory
from app.models.packages.package_customization import PackageCustomization
from app.models.packages.package_discount import PackageDiscount
from app.models.packages.package_faq import PackageFAQ
from app.models.packages.package_gallery import PackageGallery
from app.models.packages.package_item import PackageItem, package_item_links
from app.models.packages.package_item_image import PackageItemImage
from app.models.packages.package_item_like import PackageItemLike
from app.models.packages.package_item_review import PackageItemReview
from app.models.packages.package_item_vendor import PackageItemVendor
from app.models.packages.package_like import PackageLike
from app.models.packages.package_pricing import PackagePricing
from app.models.packages.package_review import PackageReview
from app.repositories.base import BaseRepository


class PackageRepository(BaseRepository[Package]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Package)

    async def find_by_slug(self, slug: str) -> Package | None:
        return await self.find_one(Package.slug == slug)

    async def find_active(self, *, skip: int = 0, limit: int = 100) -> list[Package]:
        return await self.find_many(
            Package.is_active == True,  # noqa: E712
            skip=skip,
            limit=limit,
        )

    async def find_featured(self, *, limit: int = 20) -> list[Package]:
        return await self.find_many(
            Package.is_featured == True,  # noqa: E712
            Package.is_active == True,  # noqa: E712
            order_by=Package.display_order.asc(),
            limit=limit,
        )

    async def find_bestsellers(self, *, limit: int = 20) -> list[Package]:
        return await self.find_many(
            Package.is_bestseller == True,  # noqa: E712
            Package.is_active == True,  # noqa: E712
            limit=limit,
        )

    async def find_by_category(
        self,
        category_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Package]:
        return await self.find_many(
            Package.category_id == category_id,
            Package.is_active == True,  # noqa: E712
            skip=skip,
            limit=limit,
        )

    async def find_by_occasion(
        self,
        occasion_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Package]:
        return await self.find_many(
            Package.occasion_id == occasion_id,
            Package.is_active == True,  # noqa: E712
            skip=skip,
            limit=limit,
        )

    async def find_in_price_range(
        self,
        min_price: Decimal,
        max_price: Decimal,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Package]:
        return await self.find_many(
            Package.base_price >= min_price,
            Package.base_price <= max_price,
            Package.is_active == True,  # noqa: E712
            order_by=Package.base_price.asc(),
            skip=skip,
            limit=limit,
        )

    async def get_with_items(self, package_id: uuid.UUID) -> Package | None:
        return await self.get_by_id(
            package_id,
            options=[selectinload(Package.items)],
        )

    async def get_with_pricing(self, package_id: uuid.UUID) -> Package | None:
        return await self.get_by_id(
            package_id,
            options=[selectinload(Package.pricings)],
        )

    async def get_full(self, package_id: uuid.UUID) -> Package | None:
        return await self.get_by_id(
            package_id,
            options=[
                selectinload(Package.items),
                selectinload(Package.pricings),
                selectinload(Package.addons),
                selectinload(Package.gallery),
            ],
        )


class PackageCategoryRepository(BaseRepository[PackageCategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageCategory)

    async def find_active(self) -> list[PackageCategory]:
        return await self.find_many(
            PackageCategory.is_active == True,  # noqa: E712
            order_by=PackageCategory.sort_order.asc(),
        )

    async def find_by_slug(self, slug: str) -> PackageCategory | None:
        return await self.find_one(PackageCategory.slug == slug)


class PackageItemRepository(BaseRepository[PackageItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageItem)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageItem]:
        return await self.find_many(
            PackageItem.package_id == package_id,
            order_by=PackageItem.display_order.asc(),
        )

    async def find_with_vendors(self, package_id: uuid.UUID) -> list[PackageItem]:
        return await self.find_many(
            PackageItem.package_id == package_id,
            options=[selectinload(PackageItem.vendor_assignments)],
            order_by=PackageItem.display_order.asc(),
        )

    async def find_by_package_including_common(self, package_id: uuid.UUID) -> list[PackageItem]:
        """Package-specific items plus any common items linked via package_item_links."""
        direct_stmt = select(PackageItem).where(PackageItem.package_id == package_id)
        linked_stmt = (
            select(PackageItem)
            .join(package_item_links, package_item_links.c.package_item_id == PackageItem.id)
            .where(package_item_links.c.package_id == package_id)
        )
        direct = (await self._session.execute(direct_stmt)).scalars().all()
        linked = (await self._session.execute(linked_stmt)).scalars().all()
        combined = list(direct) + [i for i in linked if i.id not in {d.id for d in direct}]
        combined.sort(key=lambda i: i.display_order)
        return combined

    async def find_common_for_vendor(self, vendor_id: uuid.UUID) -> list[PackageItem]:
        return await self.find_many(
            PackageItem.vendor_id == vendor_id,
            PackageItem.is_common == True,  # noqa: E712
            order_by=PackageItem.display_order.asc(),
        )

    async def link_to_package(self, package_id: uuid.UUID, item_id: uuid.UUID) -> None:
        stmt = (
            postgresql.insert(package_item_links)
            .values(package_id=package_id, package_item_id=item_id)
            .on_conflict_do_nothing()
        )
        await self._session.execute(stmt)

    async def unlink_from_package(self, package_id: uuid.UUID, item_id: uuid.UUID) -> None:
        stmt = package_item_links.delete().where(
            package_item_links.c.package_id == package_id,
            package_item_links.c.package_item_id == item_id,
        )
        await self._session.execute(stmt)

    async def is_linked_to_package(self, package_id: uuid.UUID, item_id: uuid.UUID) -> bool:
        stmt = select(package_item_links.c.package_id).where(
            package_item_links.c.package_id == package_id,
            package_item_links.c.package_item_id == item_id,
        )
        result = await self._session.execute(stmt)
        return result.first() is not None


class PackageItemImageRepository(BaseRepository[PackageItemImage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageItemImage)

    async def find_by_item(self, item_id: uuid.UUID) -> list[PackageItemImage]:
        return await self.find_many(
            PackageItemImage.item_id == item_id,
            order_by=PackageItemImage.sort_order.asc(),
        )

    async def find_by_items(self, item_ids: list[uuid.UUID]) -> list[PackageItemImage]:
        return await self.find_many(
            PackageItemImage.item_id.in_(item_ids),
            order_by=PackageItemImage.sort_order.asc(),
        )


class PackageItemVendorRepository(BaseRepository[PackageItemVendor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageItemVendor)

    async def find_by_item(self, item_id: uuid.UUID) -> list[PackageItemVendor]:
        return await self.find_many(PackageItemVendor.package_item_id == item_id)

    async def find_by_vendor(self, vendor_id: uuid.UUID) -> list[PackageItemVendor]:
        return await self.find_many(PackageItemVendor.vendor_id == vendor_id)


class PackageAddonRepository(BaseRepository[PackageAddon]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageAddon)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageAddon]:
        return await self.find_many(PackageAddon.package_id == package_id)

    async def find_active_for_package(self, package_id: uuid.UUID) -> list[PackageAddon]:
        return await self.find_many(
            PackageAddon.package_id == package_id,
            PackageAddon.is_active == True,  # noqa: E712
        )


class PackagePricingRepository(BaseRepository[PackagePricing]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackagePricing)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackagePricing]:
        return await self.find_many(PackagePricing.package_id == package_id)

    async def find_active_for_package(self, package_id: uuid.UUID) -> list[PackagePricing]:
        return await self.find_many(
            PackagePricing.package_id == package_id,
            PackagePricing.is_active == True,  # noqa: E712
        )


class PackageDiscountRepository(BaseRepository[PackageDiscount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageDiscount)

    async def find_active_for_package(self, package_id: uuid.UUID) -> list[PackageDiscount]:
        return await self.find_many(
            PackageDiscount.package_id == package_id,
            PackageDiscount.is_active == True,  # noqa: E712
        )


class PackageAvailabilityRepository(BaseRepository[PackageAvailability]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageAvailability)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageAvailability]:
        return await self.find_many(PackageAvailability.package_id == package_id)


class PackageGalleryRepository(BaseRepository[PackageGallery]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageGallery)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageGallery]:
        return await self.find_many(
            PackageGallery.package_id == package_id,
            order_by=PackageGallery.sort_order.asc(),
        )


class PackageReviewRepository(BaseRepository[PackageReview]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageReview)

    async def find_by_package(
        self,
        package_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PackageReview]:
        return await self.find_many(
            PackageReview.package_id == package_id,
            order_by=PackageReview.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_customer(self, customer_id: uuid.UUID) -> list[PackageReview]:
        return await self.find_many(PackageReview.customer_id == customer_id)


class PackageItemReviewRepository(BaseRepository[PackageItemReview]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageItemReview)

    async def find_by_item(
        self,
        package_item_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PackageItemReview]:
        return await self.find_many(
            PackageItemReview.package_item_id == package_item_id,
            order_by=PackageItemReview.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_customer(self, customer_id: uuid.UUID) -> list[PackageItemReview]:
        return await self.find_many(PackageItemReview.customer_id == customer_id)


class PackageLikeRepository(BaseRepository[PackageLike]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageLike)

    async def find_by_user_and_package(
        self, user_id: uuid.UUID, package_id: uuid.UUID
    ) -> PackageLike | None:
        return await self.find_one(
            PackageLike.user_id == user_id,
            PackageLike.package_id == package_id,
        )


class PackageItemLikeRepository(BaseRepository[PackageItemLike]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageItemLike)

    async def find_by_user_and_item(
        self, user_id: uuid.UUID, package_item_id: uuid.UUID
    ) -> PackageItemLike | None:
        return await self.find_one(
            PackageItemLike.user_id == user_id,
            PackageItemLike.package_item_id == package_item_id,
        )


class PackageFAQRepository(BaseRepository[PackageFAQ]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageFAQ)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageFAQ]:
        return await self.find_many(
            PackageFAQ.package_id == package_id,
            order_by=PackageFAQ.display_order.asc(),
        )


class PackageCustomizationRepository(BaseRepository[PackageCustomization]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PackageCustomization)

    async def find_by_package(self, package_id: uuid.UUID) -> list[PackageCustomization]:
        return await self.find_many(PackageCustomization.package_id == package_id)


class PackageRepositoryAggregate:
    """Groups all package-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.packages = PackageRepository(session)
        self.categories = PackageCategoryRepository(session)
        self.items = PackageItemRepository(session)
        self.item_images = PackageItemImageRepository(session)
        self.item_vendors = PackageItemVendorRepository(session)
        self.addons = PackageAddonRepository(session)
        self.pricings = PackagePricingRepository(session)
        self.discounts = PackageDiscountRepository(session)
        self.availability = PackageAvailabilityRepository(session)
        self.gallery = PackageGalleryRepository(session)
        self.reviews = PackageReviewRepository(session)
        self.item_reviews = PackageItemReviewRepository(session)
        self.likes = PackageLikeRepository(session)
        self.item_likes = PackageItemLikeRepository(session)
        self.faqs = PackageFAQRepository(session)
        self.customizations = PackageCustomizationRepository(session)
