"""
Pure helper functions for the users service domain — no I/O, no database access.
"""

from __future__ import annotations


def mask_phone(phone: str) -> str:
    """
    Return a masked phone string.

    E.164 Indian format (+91XXXXXXXXXX) → "+91XXXXXX1234".
    For non-standard lengths, mask everything except the last 4 digits.
    """
    if len(phone) >= 4:
        visible_suffix = phone[-4:]
        prefix = phone[:3] if phone.startswith("+") else phone[:2]
        mask_len = len(phone) - len(prefix) - 4
        return f"{prefix}{'X' * max(mask_len, 0)}{visible_suffix}"
    return phone


def mask_email(email: str) -> str:
    """
    Return a masked email string.

    "johndoe@gmail.com" → "jo**@gmail.com"
    At least 2 characters are always shown; the rest of the local part is masked.
    """
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local}@{domain}"
    visible = local[:2]
    masked = "*" * (len(local) - 2)
    return f"{visible}{masked}@{domain}"


def normalize_phone(phone: str) -> str:
    """
    Strip whitespace and ensure the number has a +91 country-code prefix.

    Accepts:
        "+919876543210"   → "+919876543210"
        "09876543210"     → "+919876543210"
        "9876543210"      → "+919876543210"
    """
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        return phone
    if phone.startswith("91") and len(phone) == 12:
        return "+" + phone
    if phone.startswith("0") and len(phone) == 11:
        return "+91" + phone[1:]
    if len(phone) == 10:
        return "+91" + phone
    return phone
