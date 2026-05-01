"""add prorata_pct to documents

Revision ID: 20260501_0009
Revises: 20260425_0008
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260501_0009"
down_revision = "20260425_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("prorata_pct", sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "prorata_pct")
