"""
Paginated list response types for the vendors domain.

Each type alias wires a CursorPage to the appropriate response schema
so FastAPI can generate accurate OpenAPI response models.
"""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.vendors.response import (
    VendorResponse,
    VendorServiceResponse,
    VendorReviewResponse,
)

__all__ = [
    "VendorPage",
    "VendorServicePage",
    "VendorReviewPage",
]

VendorPage = CursorPage[VendorResponse]
"""Paginated list of public vendor records."""

VendorServicePage = CursorPage[VendorServiceResponse]
"""Paginated list of vendor service offerings."""

VendorReviewPage = CursorPage[VendorReviewResponse]
"""Paginated list of vendor reviews."""
