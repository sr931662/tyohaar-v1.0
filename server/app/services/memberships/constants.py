from __future__ import annotations

from decimal import Decimal

TRIAL_PERIOD_DAYS = 0  # no trial by default
MAX_PLAN_PRICE = Decimal("99999.00")
MIN_PLAN_PRICE = Decimal("0.00")  # free tier allowed
RENEWAL_REMINDER_DAYS_BEFORE = 7
MAX_ACTIVE_MEMBERSHIP_PER_USER = 1  # only one active at a time
