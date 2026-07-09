"""create feedback table

Revision ID: f1a2b3c4d5e6
Revises: e6bc39bdb036
Create Date: 2026-07-09 00:00:00.000000

Uses IF NOT EXISTS guard so the migration is idempotent everywhere,
matching the convention used by a6b7c8d9e0f1_create_support_tables.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e6bc39bdb036'
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

    if not _table_exists(conn, "feedback"):
        op.create_table(
            'feedback',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('rating', sa.SmallInteger(), nullable=False),
            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('comments', sa.Text(), nullable=True),
            sa.Column('app_version', sa.String(20), nullable=True),

            sa.Column('is_reviewed', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('reviewed_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_feedback_rating_range'),
        )
        op.create_index('ix_feedback_customer_id', 'feedback', ['customer_id'])
        op.create_index('ix_feedback_category', 'feedback', ['category'])
        op.create_index('ix_feedback_created_at', 'feedback', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "feedback"):
        op.drop_index('ix_feedback_created_at', table_name='feedback')
        op.drop_index('ix_feedback_category', table_name='feedback')
        op.drop_index('ix_feedback_customer_id', table_name='feedback')
        op.drop_table('feedback')
