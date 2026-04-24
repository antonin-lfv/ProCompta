"""add amount_ttc_eur to documents

Revision ID: 20260424_0004
Revises: 20260424_0003
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_0004"
down_revision = "20260424_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("amount_ttc_eur", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "amount_ttc_eur")
