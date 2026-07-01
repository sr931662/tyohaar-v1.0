"""backfill city_slug on packages from vendor operating_cities

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-01 00:00:00.000000

Existing packages that were created before city_slug was introduced have
city_slug = NULL.  This migration backfills them by taking the first entry
in the vendor's operating_cities array (vendor_profiles.operating_cities[1]).

Packages that already have a city_slug, or whose vendor has no operating_cities
configured, are left unchanged.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE packages p
        SET city_slug = (
            SELECT vp.operating_cities[1]
            FROM vendors v
            JOIN vendor_profiles vp ON vp.vendor_id = v.id
            WHERE v.id = p.vendor_id
              AND vp.operating_cities IS NOT NULL
              AND array_length(vp.operating_cities, 1) > 0
        )
        WHERE p.city_slug IS NULL
          AND p.vendor_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM vendors v2
              JOIN vendor_profiles vp2 ON vp2.vendor_id = v2.id
              WHERE v2.id = p.vendor_id
                AND vp2.operating_cities IS NOT NULL
                AND array_length(vp2.operating_cities, 1) > 0
          )
    """))


def downgrade() -> None:
    # Cannot safely reverse a data backfill — values were NULL before
    pass
