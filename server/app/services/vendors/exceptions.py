"""
Vendors service — domain-specific exception types.
"""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionError,
)


class VendorNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Vendor", identifier)


class VendorAlreadyExistsError(ConflictError):
    default_message = "A vendor account already exists for this user."


class VendorOwnershipError(PermissionError):
    default_message = "You do not have permission to modify this vendor."


class VendorGalleryLimitError(BusinessRuleError):
    default_message = f"Gallery limit reached. A vendor may have at most 20 gallery images."


class VendorBankLimitError(BusinessRuleError):
    default_message = "Bank account limit reached. A vendor may have at most 3 bank accounts."


class DuplicateReviewError(ConflictError):
    default_message = "You have already submitted a review for this vendor."


class VendorNotVerifiedError(BusinessRuleError):
    default_message = "This vendor has not been verified yet."


class VendorDocumentNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("VendorDocument", identifier)
