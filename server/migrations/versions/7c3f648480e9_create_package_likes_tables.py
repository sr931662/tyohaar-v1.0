"""create package_likes and package_item_likes tables

Revision ID: 7c3f648480e9
Revises: 5c4108121122
Create Date: 2026-07-24 00:03:00.000000

Uses IF NOT EXISTS guard so the migration is idempotent everywhere,
matching the convention used by f1a2b3c4d5e6_create_feedback_table.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '7c3f648480e9'
down_revision: Union[str, None] = '5c4108121122'
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

    if not _table_exists(conn, "package_likes"):
        op.create_table(
            'package_likes',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('package_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False),

            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'package_id', name='uq_package_likes_user_package'),
        )
        op.create_index('ix_package_likes_package_id', 'package_likes', ['package_id'])
        op.create_index('ix_package_likes_user_id', 'package_likes', ['user_id'])

    if not _table_exists(conn, "package_item_likes"):
        op.create_table(
            'package_item_likes',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('package_item_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('package_items.id', ondelete='CASCADE'), nullable=False),

            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'package_item_id', name='uq_package_item_likes_user_item'),
        )
        op.create_index('ix_package_item_likes_package_item_id', 'package_item_likes', ['package_item_id'])
        op.create_index('ix_package_item_likes_user_id', 'package_item_likes', ['user_id'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "package_item_likes"):
        op.drop_index('ix_package_item_likes_user_id', table_name='package_item_likes')
        op.drop_index('ix_package_item_likes_package_item_id', table_name='package_item_likes')
        op.drop_table('package_item_likes')
    if _table_exists(conn, "package_likes"):
        op.drop_index('ix_package_likes_user_id', table_name='package_likes')
        op.drop_index('ix_package_likes_package_id', table_name='package_likes')
        op.drop_table('package_likes')
