"""create user_memberships table

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-01 00:00:00.000000

Table was created outside Alembic in some environments via create_all().
Uses IF NOT EXISTS guard so the migration is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a6b7c8d9e0f1'
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

    if not _table_exists(conn, "user_memberships"):
        op.create_table(
            'user_memberships',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),

            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('plan_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('membership_plans.id', ondelete='RESTRICT'), nullable=False),

            sa.Column('membership_status', sa.String(30), nullable=False, server_default='pending'),
            sa.Column('billing_cycle', sa.String(20), nullable=False),
            sa.Column('is_lifetime', sa.Boolean(), nullable=False, server_default='false'),

            sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_renewal_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('grace_period_until', sa.DateTime(timezone=True), nullable=True),

            sa.Column('auto_renew', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('renewal_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('renewal_history', postgresql.JSONB(), nullable=True),

            sa.Column('payment_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),

            sa.Column('upgraded_from_plan_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('membership_plans.id', ondelete='SET NULL'), nullable=True),
            sa.Column('upgrade_reason', sa.String(300), nullable=True),

            sa.Column('cancellation_reason', sa.String(50), nullable=True),
            sa.Column('cancellation_notes', sa.Text(), nullable=True),
            sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cancelled_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('renewal_count >= 0', name='ck_user_memberships_renewal_count_non_negative'),
        )
        op.create_index('ix_user_memberships_user_id', 'user_memberships', ['user_id'])
        op.create_index('ix_user_memberships_plan_id', 'user_memberships', ['plan_id'])
        op.create_index('ix_user_memberships_status', 'user_memberships', ['membership_status'])
        op.create_index('ix_user_memberships_expires_at', 'user_memberships', ['expires_at'])
        op.create_index(
            'ix_user_memberships_unique_active',
            'user_memberships',
            ['user_id'],
            unique=True,
            postgresql_where=sa.text("membership_status = 'active'"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "user_memberships"):
        op.drop_index('ix_user_memberships_unique_active', table_name='user_memberships')
        op.drop_index('ix_user_memberships_expires_at', table_name='user_memberships')
        op.drop_index('ix_user_memberships_status', table_name='user_memberships')
        op.drop_index('ix_user_memberships_plan_id', table_name='user_memberships')
        op.drop_index('ix_user_memberships_user_id', table_name='user_memberships')
        op.drop_table('user_memberships')
