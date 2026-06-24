"""
Vendors Routes — vendor profile, documents, gallery, availability, bank accounts, and reviews.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.vendors import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.vendors import (
    VendorBankAccountResponse,
    VendorDocumentResponse,
    VendorProfileResponse,
    VendorResponse,
    VendorReviewResponse,
)
from app.services.vendors.service import (
    VendorAvailabilityResponse,
    VendorGalleryResponse,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])

# ── Core vendor CRUD ──────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.create_vendor,
    methods=["POST"],
    response_model=SuccessResponse[VendorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Vendor Profile",
    description="Register a new vendor profile for the authenticated vendor user.",
    operation_id="vendors_create_vendor",
)

router.add_api_route(
    "",
    ctrl.list_vendors,
    methods=["GET"],
    response_model=CursorPaginatedResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="List Vendors",
    description="Return a cursor-paginated list of vendors, optionally filtered by category, location, and status.",
    operation_id="vendors_list_vendors",
)

router.add_api_route(
    "/me",
    ctrl.get_my_vendor,
    methods=["GET"],
    response_model=SuccessResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="Get My Vendor Profile",
    description="Return the vendor profile associated with the authenticated vendor user.",
    operation_id="vendors_get_my_vendor",
)

router.add_api_route(
    "/{vendor_id}",
    ctrl.get_vendor,
    methods=["GET"],
    response_model=SuccessResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Vendor",
    description="Return a single vendor profile by ID. Public endpoint.",
    operation_id="vendors_get_vendor",
)

router.add_api_route(
    "/{vendor_id}/profile",
    ctrl.update_vendor_profile,
    methods=["PUT"],
    response_model=SuccessResponse[VendorProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Vendor Profile",
    description="Update extended profile fields for a vendor. Vendor ownership required.",
    operation_id="vendors_update_vendor_profile",
)

# ── Documents ─────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/documents",
    ctrl.list_documents,
    methods=["GET"],
    response_model=SuccessResponse[list[VendorDocumentResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Vendor Documents",
    description="Return all compliance documents uploaded by the vendor.",
    operation_id="vendors_list_documents",
)

router.add_api_route(
    "/{vendor_id}/documents",
    ctrl.add_document,
    methods=["POST"],
    response_model=SuccessResponse[VendorDocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Vendor Document",
    description="Upload a new compliance document for the vendor. Vendor ownership required.",
    operation_id="vendors_add_document",
)

router.add_api_route(
    "/{vendor_id}/documents/{doc_id}",
    ctrl.update_document,
    methods=["PUT"],
    response_model=SuccessResponse[VendorDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Vendor Document",
    description="Update metadata on an existing vendor document. Vendor ownership required.",
    operation_id="vendors_update_document",
)

router.add_api_route(
    "/{vendor_id}/documents/{doc_id}",
    ctrl.delete_document,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Vendor Document",
    description="Remove a compliance document from the vendor's profile.",
    operation_id="vendors_delete_document",
)

# ── Gallery ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/gallery",
    ctrl.list_gallery,
    methods=["GET"],
    response_model=SuccessResponse[list[VendorGalleryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Vendor Gallery",
    description="Return all gallery items (images/videos) for the vendor.",
    operation_id="vendors_list_gallery",
)

router.add_api_route(
    "/{vendor_id}/gallery",
    ctrl.add_gallery_item,
    methods=["POST"],
    response_model=SuccessResponse[VendorGalleryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Gallery Item",
    description="Add a new media item to the vendor's gallery. Vendor ownership required.",
    operation_id="vendors_add_gallery_item",
)

router.add_api_route(
    "/{vendor_id}/gallery/{item_id}",
    ctrl.delete_gallery_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Gallery Item",
    description="Remove a gallery item from the vendor's profile.",
    operation_id="vendors_delete_gallery_item",
)

# ── Availability ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/availability/check",
    ctrl.check_availability,
    methods=["GET"],
    response_model=SuccessResponse[bool],
    status_code=status.HTTP_200_OK,
    summary="Check Vendor Availability",
    description="Check whether the vendor is available for a specific date/time window.",
    operation_id="vendors_check_availability",
)

router.add_api_route(
    "/{vendor_id}/availability",
    ctrl.get_availability,
    methods=["GET"],
    response_model=SuccessResponse[list[VendorAvailabilityResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Vendor Availability",
    description="Return availability slots for the vendor, optionally filtered by date range.",
    operation_id="vendors_get_availability",
)

router.add_api_route(
    "/{vendor_id}/availability",
    ctrl.set_availability,
    methods=["POST"],
    response_model=SuccessResponse[VendorAvailabilityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set Availability Slot",
    description="Create a new availability slot for the vendor. Vendor ownership required.",
    operation_id="vendors_set_availability",
)

router.add_api_route(
    "/{vendor_id}/availability/{slot_id}",
    ctrl.update_availability,
    methods=["PUT"],
    response_model=SuccessResponse[VendorAvailabilityResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Availability Slot",
    description="Modify an existing availability slot. Vendor ownership required.",
    operation_id="vendors_update_availability",
)

router.add_api_route(
    "/{vendor_id}/availability/{slot_id}",
    ctrl.delete_availability,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Availability Slot",
    description="Remove an availability slot from the vendor's calendar.",
    operation_id="vendors_delete_availability",
)

# ── Bank accounts ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/bank-accounts",
    ctrl.list_bank_accounts,
    methods=["GET"],
    response_model=SuccessResponse[list[VendorBankAccountResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Bank Accounts",
    description="Return all bank accounts registered by the vendor.",
    operation_id="vendors_list_bank_accounts",
)

router.add_api_route(
    "/{vendor_id}/bank-accounts",
    ctrl.add_bank_account,
    methods=["POST"],
    response_model=SuccessResponse[VendorBankAccountResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Bank Account",
    description="Register a bank account for vendor payouts. Vendor ownership required.",
    operation_id="vendors_add_bank_account",
)

router.add_api_route(
    "/{vendor_id}/bank-accounts/{bank_id}",
    ctrl.update_bank_account,
    methods=["PUT"],
    response_model=SuccessResponse[VendorBankAccountResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Bank Account",
    description="Update details of an existing bank account. Vendor ownership required.",
    operation_id="vendors_update_bank_account",
)

router.add_api_route(
    "/{vendor_id}/bank-accounts/{bank_id}",
    ctrl.delete_bank_account,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Bank Account",
    description="Remove a bank account from the vendor's payout accounts.",
    operation_id="vendors_delete_bank_account",
)

# ── Reviews ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/reviews",
    ctrl.list_reviews,
    methods=["GET"],
    response_model=CursorPaginatedResponse[VendorReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List Vendor Reviews",
    description="Return a cursor-paginated list of approved reviews for the vendor.",
    operation_id="vendors_list_reviews",
)

router.add_api_route(
    "/{vendor_id}/reviews",
    ctrl.add_review,
    methods=["POST"],
    response_model=SuccessResponse[VendorReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Vendor Review",
    description="Submit a review for a vendor. Customer role required.",
    operation_id="vendors_add_review",
)

router.add_api_route(
    "/{vendor_id}/reviews/{review_id}",
    ctrl.update_review,
    methods=["PUT"],
    response_model=SuccessResponse[VendorReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Vendor Review",
    description="Edit an existing review. Only the original reviewer may update it.",
    operation_id="vendors_update_review",
)

router.add_api_route(
    "/{vendor_id}/reviews/{review_id}",
    ctrl.delete_review,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Vendor Review",
    description="Remove a review. Only the original reviewer may delete it.",
    operation_id="vendors_delete_review",
)

# ── Admin operations ──────────────────────────────────────────────────────────

router.add_api_route(
    "/{vendor_id}/verify",
    ctrl.verify_vendor,
    methods=["POST"],
    response_model=SuccessResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify Vendor (Admin)",
    description="Approve or reject a vendor verification request. Admin access required.",
    operation_id="vendors_verify_vendor",
)

router.add_api_route(
    "/{vendor_id}/categories",
    ctrl.update_vendor_categories,
    methods=["PUT"],
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    summary="Update Vendor Categories (Admin)",
    description="Replace the full set of category assignments for a vendor. Admin access required.",
    operation_id="vendors_update_vendor_categories",
)
