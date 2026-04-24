"""add ocr_text to documents

Revision ID: 20260424_0003
Revises: 20260423_0002
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260424_0003"
down_revision = "20260423_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "ocr_text")
