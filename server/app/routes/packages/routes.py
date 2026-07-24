"""
Packages Routes — package CRUD, items, availability, reviews, and categories.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.packages import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.packages import (
    LikeToggleResponse,
    PackageAvailabilityResponse,
    PackageCategoryResponse,
    PackageDetailResponse,
    PackageGalleryResponse,
    PackageItemImageResponse,
    PackageItemResponse,
    PackageItemReviewResponse,
    PackageResponse,
    PackageReviewResponse,
)

router = APIRouter(prefix="/packages", tags=["Packages"])

# ── Categories (static — must precede /{package_id}) ─────────────────────────

router.add_api_route(
    "/categories",
    ctrl.list_categories,
    methods=["GET"],
    response_model=SuccessResponse[list[PackageCategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Package Categories",
    description="Return all active package categories. Public endpoint.",
    operation_id="packages_list_categories",
)

router.add_api_route(
    "/categories",
    ctrl.create_category,
    methods=["POST"],
    response_model=SuccessResponse[PackageCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Package Category (Admin)",
    description="Create a new package category. Admin access required.",
    operation_id="packages_create_category",
)

router.add_api_route(
    "/categories/{cat_id}",
    ctrl.update_category,
    methods=["PUT"],
    response_model=SuccessResponse[PackageCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Package Category (Admin)",
    description="Update an existing package category. Admin access required.",
    operation_id="packages_update_category",
)

router.add_api_route(
    "/categories/{cat_id}",
    ctrl.delete_category,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Category (Admin)",
    description="Delete a package category. Admin access required.",
    operation_id="packages_delete_category",
)

# ── Package CRUD ──────────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.list_packages,
    methods=["GET"],
    response_model=CursorPaginatedResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="List Packages",
    description="Return a cursor-paginated list of packages with optional filters. Public endpoint.",
    operation_id="packages_list_packages",
)

router.add_api_route(
    "",
    ctrl.create_package,
    methods=["POST"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Package",
    description="Create a new service package. Vendor role required.",
    operation_id="packages_create_package",
)

router.add_api_route(
    "/vendor/mine",
    ctrl.list_vendor_packages,
    methods=["GET"],
    response_model=CursorPaginatedResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Packages (Vendor)",
    description=(
        "Return the authenticated vendor's own packages across every lifecycle "
        "state (draft, pending review, active, ...). Vendor role required. "
        "Scoped server-side to the caller's vendor_id — never trusts a "
        "client-supplied vendor filter."
    ),
    operation_id="packages_list_vendor_packages",
)

router.add_api_route(
    "/{package_id}",
    ctrl.get_package,
    methods=["GET"],
    response_model=SuccessResponse[PackageDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Package",
    description="Return full details for a single package including items and availability. Public endpoint.",
    operation_id="packages_get_package",
)

router.add_api_route(
    "/{package_id}",
    ctrl.update_package,
    methods=["PUT"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Package",
    description="Update top-level fields on a package. Vendor ownership required.",
    operation_id="packages_update_package",
)

router.add_api_route(
    "/{package_id}",
    ctrl.delete_package,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package",
    description="Soft-delete a package. Vendor ownership required.",
    operation_id="packages_delete_package",
)

router.add_api_route(
    "/{package_id}/publish",
    ctrl.publish_package,
    methods=["POST"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit Package for Review",
    description="Vendor submits a draft package for admin review (DRAFT → PENDING_REVIEW). Vendor ownership required.",
    operation_id="packages_publish_package",
)

router.add_api_route(
    "/{package_id}/unpublish",
    ctrl.unpublish_package,
    methods=["POST"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="Unpublish Package",
    description="Hide the package from public listings. Vendor ownership required.",
    operation_id="packages_unpublish_package",
)

router.add_api_route(
    "/{package_id}/approve",
    ctrl.approve_package,
    methods=["POST"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="Approve Package (Admin)",
    description="Admin approves a pending package, making it publicly active (PENDING_REVIEW → ACTIVE). Admin access required.",
    operation_id="packages_approve_package",
)

router.add_api_route(
    "/{package_id}/reject",
    ctrl.reject_package,
    methods=["POST"],
    response_model=SuccessResponse[PackageResponse],
    status_code=status.HTTP_200_OK,
    summary="Reject Package (Admin)",
    description="Admin rejects a pending package, returning it to draft (PENDING_REVIEW → DRAFT). Admin access required.",
    operation_id="packages_reject_package",
)

# ── Package items ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/items",
    ctrl.list_items,
    methods=["GET"],
    response_model=SuccessResponse[list[PackageItemResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Package Items",
    description="Return all items included in the package.",
    operation_id="packages_list_items",
)

router.add_api_route(
    "/{package_id}/items",
    ctrl.add_item,
    methods=["POST"],
    response_model=SuccessResponse[PackageItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Package Item",
    description="Add a new item to the package. Vendor ownership or admin access required.",
    operation_id="packages_add_item",
)

router.add_api_route(
    "/{package_id}/items/{item_id}",
    ctrl.update_item,
    methods=["PUT"],
    response_model=SuccessResponse[PackageItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Package Item",
    description="Update details on an existing package item. Vendor ownership or admin access required.",
    operation_id="packages_update_item",
)

router.add_api_route(
    "/{package_id}/items/{item_id}",
    ctrl.delete_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Item",
    description="Remove an item from the package. Vendor ownership or admin access required.",
    operation_id="packages_delete_item",
)

# ── Common (vendor-owned, reusable) package items ──────────────────────────────

router.add_api_route(
    "/vendor/common-items",
    ctrl.list_common_items,
    methods=["GET"],
    response_model=SuccessResponse[list[PackageItemResponse]],
    status_code=status.HTTP_200_OK,
    summary="List My Common Items",
    description="Return the current vendor's reusable item templates.",
    operation_id="packages_list_common_items",
)

router.add_api_route(
    "/vendor/common-items",
    ctrl.create_common_item,
    methods=["POST"],
    response_model=SuccessResponse[PackageItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Common Item",
    description="Create a reusable item template owned by the current vendor, "
                "attachable to any of that vendor's own packages.",
    operation_id="packages_create_common_item",
)

router.add_api_route(
    "/vendor/common-items/{item_id}",
    ctrl.update_common_item,
    methods=["PUT"],
    response_model=SuccessResponse[PackageItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Common Item",
    description="Update a common item template owned by the current vendor.",
    operation_id="packages_update_common_item",
)

router.add_api_route(
    "/vendor/common-items/{item_id}",
    ctrl.delete_common_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Common Item",
    description="Delete a common item template owned by the current vendor.",
    operation_id="packages_delete_common_item",
)

router.add_api_route(
    "/{package_id}/common-items/{item_id}",
    ctrl.attach_common_item,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Attach Common Item",
    description="Attach one of the vendor's common item templates to this package.",
    operation_id="packages_attach_common_item",
)

router.add_api_route(
    "/{package_id}/common-items/{item_id}",
    ctrl.detach_common_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Detach Common Item",
    description="Detach a common item template from this package (does not delete the template).",
    operation_id="packages_detach_common_item",
)

# ── Package gallery (additional images beyond the cover) ──────────────────────

router.add_api_route(
    "/{package_id}/gallery",
    ctrl.list_gallery,
    methods=["GET"],
    response_model=SuccessResponse[list[PackageGalleryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Package Gallery",
    description="Return additional images for the package, ordered by sort_order. Public endpoint.",
    operation_id="packages_list_gallery",
)

router.add_api_route(
    "/{package_id}/gallery",
    ctrl.add_gallery_item,
    methods=["POST"],
    response_model=SuccessResponse[PackageGalleryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Gallery Image",
    description="Add an additional image to the package's gallery. Vendor ownership or admin access required.",
    operation_id="packages_add_gallery_item",
)

router.add_api_route(
    "/{package_id}/gallery/{gallery_id}",
    ctrl.delete_gallery_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Gallery Image",
    description="Remove an image from the package's gallery. Vendor ownership or admin access required.",
    operation_id="packages_delete_gallery_item",
)

# ── Package item images ─────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/items/{item_id}/images",
    ctrl.add_item_image,
    methods=["POST"],
    response_model=SuccessResponse[PackageItemImageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Package Item Image",
    description="Add a photo to a package item. Vendor ownership or admin access required.",
    operation_id="packages_add_item_image",
)

router.add_api_route(
    "/{package_id}/items/{item_id}/images/{image_id}",
    ctrl.delete_item_image,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Item Image",
    description="Remove a photo from a package item. Vendor ownership or admin access required.",
    operation_id="packages_delete_item_image",
)

# ── Availability ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/availability",
    ctrl.list_availability,
    methods=["GET"],
    response_model=SuccessResponse[list[PackageAvailabilityResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Package Availability",
    description="Return availability slots for the package, optionally filtered by date range.",
    operation_id="packages_list_availability",
)

router.add_api_route(
    "/{package_id}/availability",
    ctrl.set_availability,
    methods=["POST"],
    response_model=SuccessResponse[PackageAvailabilityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set Package Availability",
    description="Create an availability slot for the package. Vendor ownership required.",
    operation_id="packages_set_availability",
)

router.add_api_route(
    "/{package_id}/availability/{avail_id}",
    ctrl.update_availability,
    methods=["PUT"],
    response_model=SuccessResponse[PackageAvailabilityResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Package Availability",
    description="Update an existing availability slot. Vendor ownership required.",
    operation_id="packages_update_availability",
)

router.add_api_route(
    "/{package_id}/availability/{avail_id}",
    ctrl.delete_availability,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Availability",
    description="Remove an availability slot from the package.",
    operation_id="packages_delete_availability",
)

# ── Reviews ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/reviews",
    ctrl.list_reviews,
    methods=["GET"],
    response_model=CursorPaginatedResponse[PackageReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List Package Reviews",
    description="Return a cursor-paginated list of reviews for the package.",
    operation_id="packages_list_reviews",
)

router.add_api_route(
    "/{package_id}/reviews",
    ctrl.add_review,
    methods=["POST"],
    response_model=SuccessResponse[PackageReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Package Review",
    description="Submit a review for a package. Customer role required.",
    operation_id="packages_add_review",
)

router.add_api_route(
    "/{package_id}/reviews/{review_id}",
    ctrl.delete_review,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Review",
    description="Remove a review from the package. Only the original reviewer may delete it.",
    operation_id="packages_delete_review",
)

router.add_api_route(
    "/{package_id}/reviews/{review_id}/moderate",
    ctrl.moderate_review,
    methods=["PATCH"],
    response_model=SuccessResponse[PackageReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Moderate Package Review (Admin)",
    description="Approve, reject, flag, or hide a package review. Admin access required.",
    operation_id="packages_moderate_review",
)

# ── Likes ─────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/like",
    ctrl.like_package,
    methods=["POST"],
    response_model=SuccessResponse[LikeToggleResponse],
    status_code=status.HTTP_200_OK,
    summary="Like Package",
    description="Like a package. Idempotent — liking an already-liked package is a no-op.",
    operation_id="packages_like",
)

router.add_api_route(
    "/{package_id}/like",
    ctrl.unlike_package,
    methods=["DELETE"],
    response_model=SuccessResponse[LikeToggleResponse],
    status_code=status.HTTP_200_OK,
    summary="Unlike Package",
    description="Unlike a package. Idempotent — unliking a not-liked package is a no-op.",
    operation_id="packages_unlike",
)

# ── Item Reviews ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/items/{item_id}/reviews",
    ctrl.list_item_reviews,
    methods=["GET"],
    response_model=CursorPaginatedResponse[PackageItemReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List Package Item Reviews",
    description="Return a cursor-paginated list of reviews for the package item.",
    operation_id="packages_list_item_reviews",
)

router.add_api_route(
    "/{package_id}/items/{item_id}/reviews",
    ctrl.add_item_review,
    methods=["POST"],
    response_model=SuccessResponse[PackageItemReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Package Item Review",
    description="Submit a review for a package item. Customer role required.",
    operation_id="packages_add_item_review",
)

router.add_api_route(
    "/{package_id}/items/{item_id}/reviews/{review_id}",
    ctrl.delete_item_review,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Package Item Review",
    description="Remove a review from the package item. Only the original reviewer may delete it.",
    operation_id="packages_delete_item_review",
)

router.add_api_route(
    "/{package_id}/items/{item_id}/reviews/{review_id}/moderate",
    ctrl.moderate_item_review,
    methods=["PATCH"],
    response_model=SuccessResponse[PackageItemReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Moderate Package Item Review (Admin)",
    description="Approve, reject, flag, or hide a package item review. Admin access required.",
    operation_id="packages_moderate_item_review",
)

# ── Item Likes ────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{package_id}/items/{item_id}/like",
    ctrl.like_item,
    methods=["POST"],
    response_model=SuccessResponse[LikeToggleResponse],
    status_code=status.HTTP_200_OK,
    summary="Like Package Item",
    description="Like a package item. Idempotent — liking an already-liked item is a no-op.",
    operation_id="packages_like_item",
)

router.add_api_route(
    "/{package_id}/items/{item_id}/like",
    ctrl.unlike_item,
    methods=["DELETE"],
    response_model=SuccessResponse[LikeToggleResponse],
    status_code=status.HTTP_200_OK,
    summary="Unlike Package Item",
    description="Unlike a package item. Idempotent — unliking a not-liked item is a no-op.",
    operation_id="packages_unlike_item",
)
