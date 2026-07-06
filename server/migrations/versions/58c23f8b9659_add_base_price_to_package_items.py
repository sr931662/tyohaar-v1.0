"""add base_price to package_items

Revision ID: 58c23f8b9659
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 00:00:00.000000

PackageItemCreate/Update/Response schemas have always declared a required
`base_price` field, but the package_items table never actually had that
column — every add/update/list-with-items call was failing with an
unhandled validation error (create/update raised a raw TypeError from the
ORM constructor; response serialization raised a pydantic ValidationError).

Backfills existing rows to 0.00 since there's no historical per-item price
to recover from; new rows always supply a real value going forward (both
schemas require it).
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '58c23f8b9659'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'package_items',
        sa.Column('base_price', sa.Numeric(12, 2), nullable=False, server_default='0',
                  comment='Price of this item line within the package.'),
    )
    op.alter_column('package_items', 'base_price', server_default=None)


def downgrade() -> None:
    op.drop_column('package_items', 'base_price')
