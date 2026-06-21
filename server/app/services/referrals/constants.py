"""Referrals domain — service-layer constants."""

from __future__ import annotations

from decimal import Decimal

REFERRAL_CODE_LENGTH = 8
MAX_REFERRAL_REWARD = Decimal("500.00")        # per successful referral
REFERRER_REWARD_AMOUNT = Decimal("100.00")
REFEREE_REWARD_AMOUNT = Decimal("50.00")
MIN_BOOKING_AMOUNT_FOR_REWARD = Decimal("500.00")  # referral triggers on first booking >= this
MAX_REFERRALS_PER_USER = 100
REFERRAL_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous characters

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
