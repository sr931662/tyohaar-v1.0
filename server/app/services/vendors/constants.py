"""
Vendors service — domain-wide constants.
"""

from __future__ import annotations

MAX_GALLERY_IMAGES: int = 20
MAX_BANK_ACCOUNTS: int = 3
MAX_DOCUMENTS_PER_TYPE: int = 3
MAX_AVAILABILITY_SLOTS_PER_DAY: int = 10
MIN_RATING: float = 1.0
MAX_RATING: float = 5.0
MAX_REVIEW_LENGTH: int = 1000
VENDOR_ONBOARDING_REQUIRED_DOCS: list[str] = ["aadhar", "pan", "bank_statement"]
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
