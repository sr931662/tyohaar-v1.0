from __future__ import annotations

from datetime import date, datetime, timezone


def calculate_expiry_date(start_date: date, duration_days: int) -> date:
    from datetime import timedelta
    return start_date + timedelta(days=duration_days)


def is_membership_expired(expires_at: date | None) -> bool:
    if expires_at is None:
        return False
    today = datetime.now(tz=timezone.utc).date()
    return expires_at < today


def days_until_expiry(expires_at: date) -> int:
    today = datetime.now(tz=timezone.utc).date()
    delta = expires_at - today
    return max(0, delta.days)


def is_membership_active(membership: dict) -> bool:
    from app.models.enums import MembershipStatus
    status = membership.get("membership_status")
    expires_at = membership.get("expires_at")

    if status != MembershipStatus.ACTIVE:
        return False

    if expires_at is None:
        return True

    if isinstance(expires_at, datetime):
        expires_date = expires_at.date()
    else:
        expires_date = expires_at

    return not is_membership_expired(expires_date)
