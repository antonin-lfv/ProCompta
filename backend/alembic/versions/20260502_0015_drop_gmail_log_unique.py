"""drop unique constraint on gmail_import_log.gmail_message_id

Revision ID: 20260502_0015
Revises: 20260502_0014
Create Date: 2026-05-02
"""
from alembic import op

revision = "20260502_0015"
down_revision = "20260502_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("gmail_import_log_gmail_message_id_key", "gmail_import_log", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("gmail_import_log_gmail_message_id_key", "gmail_import_log", ["gmail_message_id"])
