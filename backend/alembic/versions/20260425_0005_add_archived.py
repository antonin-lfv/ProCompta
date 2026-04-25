"""add archived to documents

Revision ID: 20260425_0005
Revises: 20260424_0004
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260425_0005"
down_revision = "20260424_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("documents", "archived")
