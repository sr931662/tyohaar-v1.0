"""create package_item_reviews table

Revision ID: 5c4108121122
Revises: 92bab569e1f8
Create Date: 2026-07-24 00:02:00.000000

Uses IF NOT EXISTS guard so the migration is idempotent everywhere,
matching the convention used by f1a2b3c4d5e6_create_feedback_table.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '5c4108121122'
down_revision: Union[str, None] = '92bab569e1f8'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "package_item_reviews"):
        op.create_table(
            'package_item_reviews',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('package_item_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('package_items.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('booking_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('bookings.id', ondelete='SET NULL'), nullable=True),

            sa.Column('rating', sa.SmallInteger(), nullable=False),
            sa.Column('title', sa.String(300), nullable=True),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('media_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

            sa.Column('is_verified_booking', sa.Boolean(), nullable=False, server_default='false'),

            sa.Column('moderation_status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('moderated_by_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('moderated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('moderation_notes', sa.Text(), nullable=True),

            sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'),

            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('package_item_id', 'customer_id', name='uq_package_item_reviews_item_customer'),
            sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_package_item_reviews_rating_range'),
            sa.CheckConstraint('helpful_count >= 0', name='ck_package_item_reviews_helpful_count'),
        )
        op.create_index('ix_package_item_reviews_package_item_id', 'package_item_reviews', ['package_item_id'])
        op.create_index('ix_package_item_reviews_customer_id', 'package_item_reviews', ['customer_id'])
        op.create_index('ix_package_item_reviews_moderation', 'package_item_reviews', ['moderation_status', 'is_published'])
        op.create_index('ix_package_item_reviews_rating', 'package_item_reviews', ['package_item_id', 'rating'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "package_item_reviews"):
        op.drop_index('ix_package_item_reviews_rating', table_name='package_item_reviews')
        op.drop_index('ix_package_item_reviews_moderation', table_name='package_item_reviews')
        op.drop_index('ix_package_item_reviews_customer_id', table_name='package_item_reviews')
        op.drop_index('ix_package_item_reviews_package_item_id', table_name='package_item_reviews')
        op.drop_table('package_item_reviews')
