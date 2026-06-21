"""Referrals domain — stateless helper functions."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal

from app.services.referrals.constants import REFERRAL_CODE_CHARS, REFERRAL_CODE_LENGTH


def generate_referral_code(user_id: uuid.UUID) -> str:
    """Generate a deterministic 8-character referral code seeded from user_id.

    Uses the first 8 bytes of the SHA-256 hash of the user_id to pick
    characters from REFERRAL_CODE_CHARS, ensuring reproducibility and
    avoiding ambiguous characters (0, O, 1, I).
    """
    digest = hashlib.sha256(str(user_id).encode()).digest()
    alphabet = REFERRAL_CODE_CHARS
    base = len(alphabet)
    code_chars: list[str] = []
    for i in range(REFERRAL_CODE_LENGTH):
        code_chars.append(alphabet[digest[i] % base])
    return "".join(code_chars)


def is_self_referral(referrer_id: uuid.UUID, referee_id: uuid.UUID) -> bool:
    """Return True when the referrer and referee are the same user."""
    return referrer_id == referee_id


def calculate_referral_reward(
    booking_amount: Decimal,
    reward_amount: Decimal,
) -> Decimal:
    """Return reward_amount unchanged (flat reward per qualifying booking).

    Extend this function if the reward becomes percentage-based in future.
    """
    return reward_amount.quantize(Decimal("0.01"))
