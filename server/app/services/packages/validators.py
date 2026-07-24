from __future__ import annotations

from uuid import UUID

from app.models.packages.package import Package
from app.models.packages.package_item import PackageItem
from app.repositories.unit_of_work import UnitOfWork
from app.services.packages.constants import MAX_ITEMS_PER_PACKAGE
from app.services.packages.exceptions import (
    DuplicatePackageItemReviewError,
    DuplicatePackageReviewError,
    PackageItemLimitError,
    PackageItemNotFoundError,
    PackageNotFoundError,
    PackageOwnershipError,
)


async def validate_package_exists(
    package_id: UUID,
    uow: UnitOfWork,
) -> Package:
    """Return the Package or raise PackageNotFoundError."""
    package = await uow.packages.packages.get_by_id(package_id)
    if package is None:
        raise PackageNotFoundError(str(package_id))
    return package


async def validate_package_ownership(
    package_id: UUID,
    vendor_id: UUID,
    uow: UnitOfWork,
) -> Package:
    """Return the Package if it exists and is owned by vendor_id."""
    package = await validate_package_exists(package_id, uow)
    if package.vendor_id != vendor_id:
        raise PackageOwnershipError(f"Vendor {vendor_id} does not own package {package_id}.")
    return package


async def validate_review_not_duplicate(
    package_id: UUID,
    reviewer_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise DuplicatePackageReviewError if the reviewer already reviewed this package."""
    existing = await uow.packages.reviews.find_one(
        uow.packages.reviews._model.package_id == package_id,
        uow.packages.reviews._model.customer_id == reviewer_id,
    )
    if existing is not None:
        raise DuplicatePackageReviewError(
            f"User {reviewer_id} has already reviewed package {package_id}."
        )


async def validate_package_item_exists(
    package_item_id: UUID,
    uow: UnitOfWork,
) -> PackageItem:
    """Return the PackageItem or raise PackageItemNotFoundError."""
    item = await uow.packages.items.get_by_id(package_item_id)
    if item is None:
        raise PackageItemNotFoundError(str(package_item_id))
    return item


async def validate_item_review_not_duplicate(
    package_item_id: UUID,
    reviewer_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise DuplicatePackageItemReviewError if the reviewer already reviewed this item."""
    existing = await uow.packages.item_reviews.find_one(
        uow.packages.item_reviews._model.package_item_id == package_item_id,
        uow.packages.item_reviews._model.customer_id == reviewer_id,
    )
    if existing is not None:
        raise DuplicatePackageItemReviewError(
            f"User {reviewer_id} has already reviewed package item {package_item_id}."
        )


async def validate_item_limit(
    package_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise PackageItemLimitError if the package already has the maximum items."""
    count = await uow.packages.items.count(
        uow.packages.items._model.package_id == package_id,
    )
    if count >= MAX_ITEMS_PER_PACKAGE:
        raise PackageItemLimitError(
            f"Package {package_id} already has {count} items "
            f"(maximum is {MAX_ITEMS_PER_PACKAGE})."
        )
