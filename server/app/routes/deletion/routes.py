"""
Deletion Routes — account closure and the purge pass.

Mounted under /account rather than /users because these endpoints act on the
account as a whole, not on the user resource. `DELETE /users/me` continues to
mean "deactivate", which is a different and reversible thing.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.deletion import controller as ctrl
from app.core.responses import SuccessResponse
from app.schemas.deletion.response import DeletionRequestResponse, PurgeRunResponse

router = APIRouter(prefix="/account", tags=["Account Deletion"])

router.add_api_route(
    "/deletion-request",
    ctrl.request_my_deletion,
    methods=["POST"],
    response_model=SuccessResponse[DeletionRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request Account Deletion",
    description=(
        "Permanently delete the authenticated user's account and personal "
        "data. The account is deactivated immediately and can be restored "
        "until the recovery date in the response; after that the purge runs "
        "and cannot be undone."
    ),
    operation_id="account_request_deletion",
)

router.add_api_route(
    "/deletion-request",
    ctrl.get_my_deletion_request,
    methods=["GET"],
    response_model=SuccessResponse[DeletionRequestResponse | None],
    status_code=status.HTTP_200_OK,
    summary="Get My Deletion Request",
    description=(
        "Return the authenticated user's most recent deletion request, or "
        "null if they have never made one."
    ),
    operation_id="account_get_deletion_request",
)

router.add_api_route(
    "/deletion-request",
    ctrl.cancel_my_deletion,
    methods=["DELETE"],
    response_model=SuccessResponse[DeletionRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel Account Deletion",
    description=(
        "Restore an account inside its recovery window. Fails once the "
        "recovery window has closed, because by then there is nothing left "
        "to restore."
    ),
    operation_id="account_cancel_deletion",
)

router.add_api_route(
    "/deletion-request/run-due",
    ctrl.run_due_purges,
    methods=["POST"],
    response_model=SuccessResponse[PurgeRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Run Due Purges",
    description=(
        "Admin-only. Purge every deletion request whose recovery window has "
        "closed. Normally driven by the scheduled job; safe to re-run."
    ),
    operation_id="account_run_due_purges",
)
