"""add vendor package fields

Revision ID: a3f8c21e9b04
Revises: def95016d0e7
Create Date: 2026-06-25 00:00:00.000000

"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a3f8c21e9b04'
down_revision: Union[str, None] = 'def95016d0e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('packages', sa.Column('vendor_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True))
    op.add_column('packages', sa.Column('short_description', sa.String(500), nullable=True))
    op.add_column('packages', sa.Column('is_customizable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('packages', sa.Column('base_price', sa.Numeric(12, 2), nullable=True))
    op.add_column('packages', sa.Column('currency', sa.String(10), nullable=False, server_default='INR'))
    op.add_column('packages', sa.Column('average_rating', sa.Numeric(3, 2), nullable=True))
    op.add_column('packages', sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('packages', sa.Column('booking_count', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_packages_vendor_id', 'packages', ['vendor_id'])


def downgrade() -> None:
    op.drop_index('ix_packages_vendor_id', 'packages')
    op.drop_column('packages', 'booking_count')
    op.drop_column('packages', 'review_count')
    op.drop_column('packages', 'average_rating')
    op.drop_column('packages', 'currency')
    op.drop_column('packages', 'base_price')
    op.drop_column('packages', 'is_customizable')
    op.drop_column('packages', 'short_description')
    op.drop_column('packages', 'vendor_id')
