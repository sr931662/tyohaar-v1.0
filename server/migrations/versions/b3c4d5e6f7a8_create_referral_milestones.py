"""create referral_milestone_rules and referral_milestone_grants

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-09 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
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

    if not _table_exists(conn, "referral_milestone_rules"):
        op.create_table(
            'referral_milestone_rules',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('referrals_required', sa.Integer(), nullable=False),
            sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False),
            sa.Column('applicable_plan_count', sa.Integer(), nullable=False),
            sa.Column('min_plan_price', sa.Numeric(12, 2), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('referrals_required > 0', name='ck_referral_milestone_referrals_required_positive'),
            sa.CheckConstraint('discount_percentage >= 0 AND discount_percentage <= 100', name='ck_referral_milestone_discount_range'),
            sa.CheckConstraint('applicable_plan_count > 0', name='ck_referral_milestone_plan_count_positive'),
        )
        op.create_index('ix_referral_milestone_rules_is_active', 'referral_milestone_rules', ['is_active'])

    if not _table_exists(conn, "referral_milestone_grants"):
        op.create_table(
            'referral_milestone_grants',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('rule_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('referral_milestone_rules.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('referral_count_at_grant', sa.Integer(), nullable=False),
            sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=False),
            sa.Column('min_plan_price', sa.Numeric(12, 2), nullable=False),
            sa.Column('plans_remaining', sa.Integer(), nullable=False),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('plans_remaining >= 0', name='ck_referral_milestone_grant_plans_non_negative'),
        )
        op.create_index('ix_referral_milestone_grants_user_id', 'referral_milestone_grants', ['user_id'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "referral_milestone_grants"):
        op.drop_index('ix_referral_milestone_grants_user_id', table_name='referral_milestone_grants')
        op.drop_table('referral_milestone_grants')
    if _table_exists(conn, "referral_milestone_rules"):
        op.drop_index('ix_referral_milestone_rules_is_active', table_name='referral_milestone_rules')
        op.drop_table('referral_milestone_rules')
