"""add gmail code verifier

Revision ID: 20260502_0014
Revises: 20260502_0013
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260502_0014"
down_revision = "20260502_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gmail_code_verifier", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gmail_code_verifier")
