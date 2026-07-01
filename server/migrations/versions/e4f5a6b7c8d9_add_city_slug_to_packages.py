"""add city_slug to packages for city-wise vendor allotment

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-01 00:00:00.000000

Adds a denormalized city_slug column to the packages table so that
GET /packages?city=noida can be answered with a simple indexed equality
filter instead of a multi-join through vendors → vendor_profiles →
operating_cities array.

Vendors set city_slug when creating a package (must match one of their
operating_cities). The mobile app passes the customer's selected city
as ?city= and sees only local packages.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'packages',
        sa.Column('city_slug', sa.String(200), nullable=True,
                  comment='City slug where this package is offered (e.g. noida, mumbai)'),
    )
    op.create_index('ix_packages_city_slug', 'packages', ['city_slug'])


def downgrade() -> None:
    op.drop_index('ix_packages_city_slug', table_name='packages')
    op.drop_column('packages', 'city_slug')
