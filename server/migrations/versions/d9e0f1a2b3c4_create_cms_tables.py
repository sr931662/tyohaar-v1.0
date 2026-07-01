"""create CMS tables: import_logs, export_logs, automation_rules, automation_logs

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-01 00:00:00.000000

Tables were created outside Alembic in some environments via create_all().
Uses IF NOT EXISTS guard so the migration is idempotent everywhere.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
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

    # ── cms_import_logs ───────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_import_logs"):
        op.create_table(
            'cms_import_logs',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('extra_metadata', postgresql.JSONB(), nullable=True),

            sa.Column('admin_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True),
            sa.Column('entity_type', sa.String(64), nullable=False),
            sa.Column('original_filename', sa.String(255), nullable=False),
            sa.Column('file_size_bytes', sa.Integer(), nullable=True),
            sa.Column('file_storage_path', sa.String(1024), nullable=True),

            sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
            sa.Column('is_dry_run', sa.Boolean(), nullable=False, server_default='false'),

            sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('invalid_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('duplicate_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('inserted_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('updated_rows', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('skipped_rows', sa.Integer(), nullable=False, server_default='0'),

            sa.Column('progress_pct', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column('error_summary', postgresql.JSONB(), nullable=True),
            sa.Column('rollback_snapshot', postgresql.JSONB(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint(
                "status IN ('PENDING','VALIDATING','PREVIEW','PROCESSING','COMPLETED','FAILED','ROLLED_BACK')",
                name='ck_import_logs_status',
            ),
            sa.CheckConstraint(
                "entity_type IN ('vendors','customers','packages','services','categories','cities','states','memberships','coupons','faqs','notification_templates','settings')",
                name='ck_import_logs_entity_type',
            ),
        )
        op.create_index('ix_import_logs_admin_id', 'cms_import_logs', ['admin_id'])
        op.create_index('ix_import_logs_entity_type', 'cms_import_logs', ['entity_type'])
        op.create_index('ix_import_logs_status', 'cms_import_logs', ['status'])
        op.create_index('ix_import_logs_created_at', 'cms_import_logs', ['created_at'])

    # ── cms_export_logs ───────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_export_logs"):
        op.create_table(
            'cms_export_logs',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('admin_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True),
            sa.Column('entity_type', sa.String(64), nullable=False),
            sa.Column('format', sa.String(8), nullable=False, server_default='XLSX'),
            sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),

            sa.Column('filters', postgresql.JSONB(), nullable=True),
            sa.Column('selected_ids', postgresql.JSONB(), nullable=True),
            sa.Column('column_selection', postgresql.JSONB(), nullable=True),

            sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('file_storage_path', sa.String(1024), nullable=True),
            sa.Column('file_size_bytes', sa.Integer(), nullable=True),
            sa.Column('download_url', sa.String(2048), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_scheduled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('schedule_cron', sa.String(64), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint(
                "status IN ('PENDING','PROCESSING','COMPLETED','FAILED','EXPIRED')",
                name='ck_export_logs_status',
            ),
            sa.CheckConstraint(
                "format IN ('XLSX','CSV','JSON')",
                name='ck_export_logs_format',
            ),
        )
        op.create_index('ix_export_logs_admin_id', 'cms_export_logs', ['admin_id'])
        op.create_index('ix_export_logs_entity_type', 'cms_export_logs', ['entity_type'])
        op.create_index('ix_export_logs_status', 'cms_export_logs', ['status'])
        op.create_index('ix_export_logs_created_at', 'cms_export_logs', ['created_at'])

    # ── cms_automation_rules ──────────────────────────────────────────────────
    if not _table_exists(conn, "cms_automation_rules"):
        op.create_table(
            'cms_automation_rules',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('created_by_admin_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True),

            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('trigger_event', sa.String(64), nullable=False),
            sa.Column('conditions', postgresql.JSONB(), nullable=True),
            sa.Column('actions', postgresql.JSONB(), nullable=False),

            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('delay_seconds', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),

            sa.Column('total_executions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('successful_executions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_executions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint(
                "trigger_event IN ("
                "'vendor.registered','vendor.approved','vendor.rejected',"
                "'booking.created','booking.confirmed','booking.completed','booking.cancelled',"
                "'payment.completed','payment.failed','payment.refunded',"
                "'membership.expiring','membership.expired','membership.renewed',"
                "'user.registered','user.inactive','referral.completed',"
                "'support.ticket_opened','support.ticket_resolved'"
                ")",
                name='ck_automation_rules_trigger_event',
            ),
        )
        op.create_index('ix_automation_rules_trigger_event', 'cms_automation_rules', ['trigger_event'])
        op.create_index('ix_automation_rules_is_active', 'cms_automation_rules', ['is_active'])
        op.create_index('ix_automation_rules_created_by', 'cms_automation_rules', ['created_by_admin_id'])

    # ── cms_automation_logs ───────────────────────────────────────────────────
    if not _table_exists(conn, "cms_automation_logs"):
        op.create_table(
            'cms_automation_logs',
            sa.Column('id', sa.UUID(), nullable=False, comment='UUID v4 primary key'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

            sa.Column('rule_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('cms_automation_rules.id', ondelete='CASCADE'), nullable=False),
            sa.Column('entity_id', sa.String(64), nullable=True),
            sa.Column('entity_type', sa.String(64), nullable=True),
            sa.Column('trigger_event', sa.String(64), nullable=False),
            sa.Column('trigger_payload', postgresql.JSONB(), nullable=True),

            sa.Column('status', sa.String(32), nullable=False, server_default='RUNNING'),
            sa.Column('actions_total', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('actions_completed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('actions_failed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('action_results', postgresql.JSONB(), nullable=True),

            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('duration_ms', sa.Integer(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),

            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint(
                "status IN ('RUNNING','COMPLETED','FAILED','RETRYING','SKIPPED')",
                name='ck_automation_logs_status',
            ),
        )
        op.create_index('ix_automation_logs_rule_id', 'cms_automation_logs', ['rule_id'])
        op.create_index('ix_automation_logs_entity_id', 'cms_automation_logs', ['entity_id'])
        op.create_index('ix_automation_logs_status', 'cms_automation_logs', ['status'])
        op.create_index('ix_automation_logs_created_at', 'cms_automation_logs', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "cms_automation_logs"):
        op.drop_table('cms_automation_logs')
    if _table_exists(conn, "cms_automation_rules"):
        op.drop_index('ix_automation_rules_created_by', table_name='cms_automation_rules')
        op.drop_index('ix_automation_rules_is_active', table_name='cms_automation_rules')
        op.drop_index('ix_automation_rules_trigger_event', table_name='cms_automation_rules')
        op.drop_table('cms_automation_rules')
    if _table_exists(conn, "cms_export_logs"):
        op.drop_index('ix_export_logs_created_at', table_name='cms_export_logs')
        op.drop_index('ix_export_logs_status', table_name='cms_export_logs')
        op.drop_index('ix_export_logs_entity_type', table_name='cms_export_logs')
        op.drop_index('ix_export_logs_admin_id', table_name='cms_export_logs')
        op.drop_table('cms_export_logs')
    if _table_exists(conn, "cms_import_logs"):
        op.drop_index('ix_import_logs_created_at', table_name='cms_import_logs')
        op.drop_index('ix_import_logs_status', table_name='cms_import_logs')
        op.drop_index('ix_import_logs_entity_type', table_name='cms_import_logs')
        op.drop_index('ix_import_logs_admin_id', table_name='cms_import_logs')
        op.drop_table('cms_import_logs')
