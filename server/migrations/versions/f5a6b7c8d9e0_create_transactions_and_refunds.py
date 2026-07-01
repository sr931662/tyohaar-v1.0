"""create transactions and refunds tables

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-01 00:00:00.000000

Tables were created outside Alembic in some environments via create_all().
Uses IF NOT EXISTS guard so the migration is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
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

    # ── transactions ──────────────────────────────────────────────────────────
    if not _table_exists(conn, "transactions"):
        op.create_table(
            'transactions',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('transaction_number', sa.String(100), nullable=False, unique=True),
            sa.Column('transaction_type', sa.String(50), nullable=False),
            sa.Column('direction', sa.String(10), nullable=False),

            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),

            sa.Column('payer_type', sa.String(20), nullable=False),
            sa.Column('payer_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('payee_type', sa.String(20), nullable=False),
            sa.Column('payee_id', postgresql.UUID(as_uuid=True), nullable=True),

            sa.Column('booking_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('bookings.id', ondelete='RESTRICT'), nullable=True),
            sa.Column('payment_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('payments.id', ondelete='RESTRICT'), nullable=True),
            sa.Column('description', sa.String(500), nullable=True),

            sa.Column('settlement_status', sa.String(30), nullable=False, server_default='pending'),
            sa.Column('settlement_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),

            sa.Column('gateway_reference', sa.String(300), nullable=True),

            sa.Column('reconciliation_status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('reconciled_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('reconciliation_notes', sa.Text(), nullable=True),

            sa.Column('is_reversal', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('reversal_of_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('transactions.id', ondelete='RESTRICT'), nullable=True),
            sa.Column('reversal_reason', sa.String(500), nullable=True),

            sa.Column('transacted_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('context_data', postgresql.JSONB(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('transaction_number', name='uq_transactions_transaction_number'),
            sa.CheckConstraint('amount > 0', name='ck_transactions_amount_positive'),
        )
        op.create_index('ix_transactions_type', 'transactions', ['transaction_type'])
        op.create_index('ix_transactions_payer', 'transactions', ['payer_type', 'payer_id'])
        op.create_index('ix_transactions_payee', 'transactions', ['payee_type', 'payee_id'])
        op.create_index('ix_transactions_payment_id', 'transactions', ['payment_id'])
        op.create_index('ix_transactions_booking_id', 'transactions', ['booking_id'])
        op.create_index('ix_transactions_settlement_status', 'transactions', ['settlement_status'])
        op.create_index('ix_transactions_reconciliation', 'transactions', ['reconciliation_status'])
        op.create_index('ix_transactions_transacted_at', 'transactions', ['transacted_at'])
        op.create_index('ix_transactions_settlement_batch', 'transactions', ['settlement_batch_id'])

    # ── refunds ───────────────────────────────────────────────────────────────
    if not _table_exists(conn, "refunds"):
        op.create_table(
            'refunds',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('payment_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('payments.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('booking_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('bookings.id', ondelete='RESTRICT'), nullable=False),

            sa.Column('refund_type', sa.String(20), nullable=False),
            sa.Column('refund_reason', sa.String(50), nullable=False),
            sa.Column('amount', sa.Numeric(12, 2), nullable=False),
            sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
            sa.Column('notes', sa.Text(), nullable=True),

            sa.Column('refund_status', sa.String(30), nullable=False),
            sa.Column('gateway_refund_id', sa.String(200), nullable=True),

            sa.Column('initiated_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('approved_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('failure_reason', sa.Text(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('amount > 0', name='ck_refund_amount_positive'),
        )
        op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'])
        op.create_index('ix_refunds_booking_id', 'refunds', ['booking_id'])
        op.create_index('ix_refunds_refund_status', 'refunds', ['refund_status'])
        op.create_index('ix_refunds_initiated_by_id', 'refunds', ['initiated_by_id'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "refunds"):
        op.drop_table('refunds')
    if _table_exists(conn, "transactions"):
        op.drop_index('ix_transactions_settlement_batch', table_name='transactions')
        op.drop_index('ix_transactions_transacted_at', table_name='transactions')
        op.drop_index('ix_transactions_reconciliation', table_name='transactions')
        op.drop_index('ix_transactions_settlement_status', table_name='transactions')
        op.drop_index('ix_transactions_booking_id', table_name='transactions')
        op.drop_index('ix_transactions_payment_id', table_name='transactions')
        op.drop_index('ix_transactions_payee', table_name='transactions')
        op.drop_index('ix_transactions_payer', table_name='transactions')
        op.drop_index('ix_transactions_type', table_name='transactions')
        op.drop_table('transactions')
