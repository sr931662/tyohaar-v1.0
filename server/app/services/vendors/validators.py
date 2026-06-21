"""
Vendors service — reusable async validator functions.

Each validator receives an active UnitOfWork (inside an `async with` block)
and either returns the requested ORM model or raises a domain exception.
"""

from __future__ import annotations

from uuid import UUID

from app.models.vendors.vendor import Vendor as VendorModel
from app.repositories.unit_of_work import UnitOfWork
from app.services.vendors.constants import MAX_BANK_ACCOUNTS, MAX_GALLERY_IMAGES
from app.services.vendors.exceptions import (
    DuplicateReviewError,
    VendorBankLimitError,
    VendorGalleryLimitError,
    VendorNotFoundError,
    VendorOwnershipError,
)


async def validate_vendor_exists(
    vendor_id: UUID,
    uow: UnitOfWork,
) -> VendorModel:
    """Return the Vendor if it exists, else raise VendorNotFoundError."""
    vendor = await uow.vendors.vendors.get_by_id(vendor_id)
    if vendor is None:
        raise VendorNotFoundError(str(vendor_id))
    return vendor


async def validate_vendor_ownership(
    vendor_id: UUID,
    user_id: UUID,
    uow: UnitOfWork,
) -> VendorModel:
    """Return the Vendor if it exists AND is owned by *user_id*.

    Raises:
        VendorNotFoundError  — vendor does not exist.
        VendorOwnershipError — vendor belongs to a different user.
    """
    vendor = await validate_vendor_exists(vendor_id, uow)
    if vendor.user_id != user_id:
        raise VendorOwnershipError()
    return vendor


async def validate_review_not_duplicate(
    vendor_id: UUID,
    reviewer_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise DuplicateReviewError if *reviewer_id* already reviewed *vendor_id*."""
    existing = await uow.vendors.reviews.find_one(
        uow.vendors.reviews._model.vendor_id == vendor_id,
        uow.vendors.reviews._model.customer_id == reviewer_id,
    )
    if existing is not None:
        raise DuplicateReviewError()


async def validate_bank_account_limit(
    vendor_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise VendorBankLimitError if the vendor already has MAX_BANK_ACCOUNTS accounts."""
    existing = await uow.vendors.bank_accounts.find_by_vendor(vendor_id)
    if len(existing) >= MAX_BANK_ACCOUNTS:
        raise VendorBankLimitError()


async def validate_gallery_limit(
    vendor_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise VendorGalleryLimitError if the vendor already has MAX_GALLERY_IMAGES items."""
    existing = await uow.vendors.gallery.find_by_vendor(vendor_id)
    if len(existing) >= MAX_GALLERY_IMAGES:
        raise VendorGalleryLimitError()
