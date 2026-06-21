from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PaymentError,
    PermissionError,
)


class MembershipPlanNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("MembershipPlan", identifier)


class MembershipNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("UserMembership", identifier)


class ActiveMembershipExistsError(ConflictError):
    default_message = "User already has an active membership."


class MembershipOwnershipError(PermissionError):
    default_message = "You do not have permission to access this membership."


class MembershipExpiredError(BusinessRuleError):
    default_message = "The membership has expired."


class PlanDeactivationBlockedError(BusinessRuleError):
    default_message = "Cannot deactivate plan: users have active memberships on this plan."


class MembershipAlreadyCancelledError(ConflictError):
    default_message = "This membership has already been cancelled."


class PaymentRequiredForPaidPlanError(PaymentError):
    default_message = "A valid payment is required to subscribe to a paid plan."
