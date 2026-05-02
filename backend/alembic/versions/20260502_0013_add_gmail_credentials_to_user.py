"""add gmail credentials to user

Revision ID: 20260502_0013
Revises: 20260502_0012
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260502_0013"
down_revision = "20260502_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gmail_client_id", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("gmail_client_secret", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("gmail_refresh_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("gmail_oauth_state", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gmail_oauth_state")
    op.drop_column("users", "gmail_refresh_token")
    op.drop_column("users", "gmail_client_secret")
    op.drop_column("users", "gmail_client_id")
