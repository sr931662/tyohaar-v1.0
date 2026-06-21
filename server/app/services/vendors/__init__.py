"""
Vendors service package.

Stable import surface:

    from app.services.vendors import VendorService
    from app.services.vendors.exceptions import VendorNotFoundError, ...
    from app.services.vendors.constants import MAX_GALLERY_IMAGES, ...
"""

from __future__ import annotations

from app.services.vendors.service import VendorService

__all__ = ["VendorService"]
