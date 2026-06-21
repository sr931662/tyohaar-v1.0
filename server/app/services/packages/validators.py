from __future__ import annotations

from uuid import UUID

from app.models.packages.package import Package
from app.repositories.unit_of_work import UnitOfWork
from app.services.packages.constants import MAX_ITEMS_PER_PACKAGE
from app.services.packages.exceptions import (
    DuplicatePackageReviewError,
    PackageItemLimitError,
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
    """
    Return the Package if it exists and is owned by vendor_id.

    Note: The Package model does not carry a direct vendor_id column (packages
    are platform-level). Ownership is established at the PackageItemVendor level.
    This validator checks existence; route-level guards enforce vendor access.
    """
    package = await validate_package_exists(package_id, uow)
    # Placeholder: real ownership logic lives in the vendor-item mapping.
    # If the package has a vendor_id field in a future migration, compare here.
    _ = vendor_id  # intentionally unused until vendor ownership column is added
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
