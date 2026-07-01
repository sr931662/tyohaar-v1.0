"""create referral_rewards table

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-01 00:00:00.000000

Table was created outside Alembic in some environments via create_all().
Uses IF NOT EXISTS guard so the migration is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
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

    if not _table_exists(conn, "referral_rewards"):
        op.create_table(
            'referral_rewards',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('referral_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('referrals.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('recipient_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),

            sa.Column('reward_type', sa.String(40), nullable=False),
            sa.Column('reward_trigger', sa.String(30), nullable=False),

            sa.Column('monetary_value', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
            sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
            sa.Column('points', sa.Integer(), nullable=False, server_default='0'),

            sa.Column('reward_status', sa.String(20), nullable=False, server_default='pending'),

            sa.Column('wallet_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('wallets.id', ondelete='RESTRICT'), nullable=True),
            sa.Column('wallet_transaction_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('wallet_transactions.id', ondelete='SET NULL'), nullable=True),

            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('approved_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

            sa.Column('is_cancelled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('cancellation_reason', sa.Text(), nullable=True),
            sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cancelled_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.Column('calculation_rule_version', sa.String(50), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('monetary_value >= 0', name='ck_referral_rewards_monetary_non_negative'),
            sa.CheckConstraint('points >= 0', name='ck_referral_rewards_points_non_negative'),
            sa.CheckConstraint('monetary_value > 0 OR points > 0', name='ck_referral_rewards_has_value'),
        )
        op.create_index('ix_referral_rewards_referral_id', 'referral_rewards', ['referral_id'])
        op.create_index('ix_referral_rewards_recipient_id', 'referral_rewards', ['recipient_id'])
        op.create_index('ix_referral_rewards_status', 'referral_rewards', ['reward_status'])
        op.create_index('ix_referral_rewards_trigger', 'referral_rewards', ['referral_id', 'reward_trigger'])
        op.create_index('ix_referral_rewards_expires_at', 'referral_rewards', ['expires_at'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "referral_rewards"):
        op.drop_index('ix_referral_rewards_expires_at', table_name='referral_rewards')
        op.drop_index('ix_referral_rewards_trigger', table_name='referral_rewards')
        op.drop_index('ix_referral_rewards_status', table_name='referral_rewards')
        op.drop_index('ix_referral_rewards_recipient_id', table_name='referral_rewards')
        op.drop_index('ix_referral_rewards_referral_id', table_name='referral_rewards')
        op.drop_table('referral_rewards')
