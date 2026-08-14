"""
Deletion Controller — account closure requested by the account owner.

Every customer-facing route here is authenticated and acts only on the caller's
own account. There is no user_id parameter anywhere: a deletion endpoint that
accepts an id is a deletion endpoint someone will eventually call with a id
that is not theirs.
"""

from __future__ import annotations

from app.core.current_user import CurrentUserDep
from app.core.dependencies import DeletionServiceDep
from app.core.permissions import AdminDep
from app.core.responses import SuccessResponse
from app.models.enums import DeletionRequestChannel
from app.schemas.deletion.response import DeletionRequestResponse, PurgeRunResponse


async def request_my_deletion(
    current_user: CurrentUserDep,
    service: DeletionServiceDep,
) -> SuccessResponse[DeletionRequestResponse]:
    request = await service.request_deletion(
        user_id=current_user.id,
        channel=DeletionRequestChannel.IN_APP,
    )
    return SuccessResponse(
        data=DeletionRequestResponse.model_validate(request),
        message=(
            "Your account has been deactivated and is scheduled for deletion. "
            "You can restore it until the recovery date shown."
        ),
    )


async def get_my_deletion_request(
    current_user: CurrentUserDep,
    service: DeletionServiceDep,
) -> SuccessResponse[DeletionRequestResponse | None]:
    request = await service.get_active_request(user_id=current_user.id)
    return SuccessResponse(
        data=(
            DeletionRequestResponse.model_validate(request)
            if request is not None
            else None
        ),
        message="Deletion request retrieved.",
    )


async def cancel_my_deletion(
    current_user: CurrentUserDep,
    service: DeletionServiceDep,
) -> SuccessResponse[DeletionRequestResponse]:
    request = await service.cancel_deletion(user_id=current_user.id)
    return SuccessResponse(
        data=DeletionRequestResponse.model_validate(request),
        message="Your account has been restored.",
    )


# ── Operational ───────────────────────────────────────────────────────────────


async def run_due_purges(
    _: AdminDep,
    service: DeletionServiceDep,
) -> SuccessResponse[PurgeRunResponse]:
    """Manually trigger the purge pass.

    The scheduled Cloud Run job is the normal driver; this exists so an
    operator can run it on demand without shell access to the container.
    """
    summary = await service.run_due()
    return SuccessResponse(
        data=PurgeRunResponse(**summary),
        message="Purge pass complete.",
    )
