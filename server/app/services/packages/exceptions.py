from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionError,
)


class PackageNotFoundError(NotFoundError):
    def __init__(self, package_id: str | None = None) -> None:
        super().__init__("Package", package_id)


class PackageOwnershipError(PermissionError):
    default_message = "You do not own this package."


class PackageItemLimitError(BusinessRuleError):
    default_message = "Package has reached the maximum number of items."


class DuplicatePackageReviewError(ConflictError):
    default_message = "You have already reviewed this package."


class PackageNotPublishedError(BusinessRuleError):
    default_message = "Package is not published and cannot be booked."
