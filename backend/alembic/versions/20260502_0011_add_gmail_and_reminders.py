"""add gmail sources, import log, reminders

Revision ID: 20260502_0011
Revises: 20260501_0010
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260502_0011"
down_revision = "20260501_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtypeenum ADD VALUE IF NOT EXISTS 'reminder_due'")

    op.create_table(
        "gmail_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sender_email", sa.String(500), nullable=False),
        sa.Column("subject_contains", sa.String(500), nullable=True),
        sa.Column("attachment_name_contains", sa.String(500), nullable=True),
        sa.Column("correspondent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["correspondent_id"], ["correspondents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "gmail_import_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("gmail_message_id", sa.String(200), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["gmail_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id"),
    )
    op.create_index("ix_gmail_import_log_gmail_message_id", "gmail_import_log", ["gmail_message_id"])

    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency_days", sa.Integer(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("notify_email", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_inapp", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reminders")
    op.drop_index("ix_gmail_import_log_gmail_message_id", table_name="gmail_import_log")
    op.drop_table("gmail_import_log")
    op.drop_table("gmail_sources")
