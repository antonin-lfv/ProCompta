"""add prorata_changed to activityeventenum

Revision ID: 20260501_0010
Revises: 20260501_0009
Create Date: 2026-05-01
"""
from alembic import op

revision = "20260501_0010"
down_revision = "20260501_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE activityeventenum ADD VALUE IF NOT EXISTS 'prorata_changed'")


def downgrade() -> None:
    pass
