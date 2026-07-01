"""create support_tickets, support_messages, support_attachments

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-01 00:00:00.000000

Tables were created outside Alembic in some environments via create_all().
Uses IF NOT EXISTS guard so the migration is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, None] = 'f5a6b7c8d9e0'
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

    # ── support_tickets ───────────────────────────────────────────────────────
    if not _table_exists(conn, "support_tickets"):
        op.create_table(
            'support_tickets',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('internal_notes', sa.Text(), nullable=True),

            sa.Column('ticket_number', sa.String(30), nullable=False),
            sa.Column('customer_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('booking_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('bookings.id', ondelete='SET NULL'), nullable=True),
            sa.Column('payment_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('payments.id', ondelete='SET NULL'), nullable=True),

            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
            sa.Column('ticket_status', sa.String(30), nullable=False, server_default='open'),

            sa.Column('subject', sa.String(300), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('resolution_summary', sa.Text(), nullable=True),

            sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('reopened_count', sa.SmallInteger(), nullable=False, server_default='0'),

            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ticket_number', name='uq_support_tickets_ticket_number'),
        )
        op.create_index('ix_support_tickets_customer_id', 'support_tickets', ['customer_id'])
        op.create_index('ix_support_tickets_assigned_agent_id', 'support_tickets', ['assigned_agent_id'])
        op.create_index('ix_support_tickets_status', 'support_tickets', ['ticket_status'])
        op.create_index('ix_support_tickets_priority', 'support_tickets', ['priority'])
        op.create_index('ix_support_tickets_booking_id', 'support_tickets', ['booking_id'])
        op.create_index('ix_support_tickets_payment_id', 'support_tickets', ['payment_id'])
        op.create_index('ix_support_tickets_sla_due', 'support_tickets', ['sla_due_at'])
        op.create_index('ix_support_tickets_last_activity', 'support_tickets', ['last_activity_at'])

    # ── support_messages ──────────────────────────────────────────────────────
    if not _table_exists(conn, "support_messages"):
        op.create_table(
            'support_messages',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('ticket_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('support_tickets.id', ondelete='RESTRICT'), nullable=False),
            sa.Column('sender_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.Column('sender_role', sa.String(20), nullable=False),
            sa.Column('message_type', sa.String(30), nullable=False, server_default='text'),

            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('edited_body', sa.Text(), nullable=True),

            sa.Column('is_internal_note', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_support_messages_ticket_id', 'support_messages', ['ticket_id'])
        op.create_index('ix_support_messages_ticket_created', 'support_messages', ['ticket_id', 'created_at'])
        op.create_index('ix_support_messages_sender_id', 'support_messages', ['sender_id'])
        op.create_index('ix_support_messages_is_internal', 'support_messages', ['ticket_id', 'is_internal_note'])

    # ── support_attachments ───────────────────────────────────────────────────
    if not _table_exists(conn, "support_attachments"):
        op.create_table(
            'support_attachments',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('ticket_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('message_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('support_messages.id', ondelete='SET NULL'), nullable=True),
            sa.Column('uploaded_by_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

            sa.Column('media_type', sa.String(20), nullable=False),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('filename', sa.String(300), nullable=False),
            sa.Column('storage_key', sa.String(500), nullable=False),
            sa.Column('storage_url', sa.String(1000), nullable=False),
            sa.Column('thumbnail_url', sa.String(1000), nullable=True),
            sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
            sa.Column('checksum', sa.String(128), nullable=True),

            sa.Column('virus_scan_status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('virus_scan_result', sa.Text(), nullable=True),
            sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_support_attachments_ticket_id', 'support_attachments', ['ticket_id'])
        op.create_index('ix_support_attachments_message_id', 'support_attachments', ['message_id'])
        op.create_index('ix_support_attachments_uploaded_by_id', 'support_attachments', ['uploaded_by_id'])
        op.create_index('ix_support_attachments_virus_scan', 'support_attachments', ['virus_scan_status'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "support_attachments"):
        op.drop_table('support_attachments')
    if _table_exists(conn, "support_messages"):
        op.drop_table('support_messages')
    if _table_exists(conn, "support_tickets"):
        op.drop_index('ix_support_tickets_last_activity', table_name='support_tickets')
        op.drop_index('ix_support_tickets_sla_due', table_name='support_tickets')
        op.drop_index('ix_support_tickets_payment_id', table_name='support_tickets')
        op.drop_index('ix_support_tickets_booking_id', table_name='support_tickets')
        op.drop_index('ix_support_tickets_priority', table_name='support_tickets')
        op.drop_index('ix_support_tickets_status', table_name='support_tickets')
        op.drop_index('ix_support_tickets_assigned_agent_id', table_name='support_tickets')
        op.drop_index('ix_support_tickets_customer_id', table_name='support_tickets')
        op.drop_table('support_tickets')
