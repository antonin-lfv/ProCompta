"""Add is_paid, is_manual to documents; make file fields nullable

Revision ID: 20260503_0016
Revises: 20260502_0015
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260503_0016"
down_revision = "20260502_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("is_paid", sa.Boolean(), nullable=True))
    op.add_column("documents", sa.Column("is_manual", sa.Boolean(), nullable=False, server_default="false"))
    op.alter_column("documents", "file_path", nullable=True)
    op.alter_column("documents", "file_hash", nullable=True)
    op.alter_column("documents", "mime_type", nullable=True)
    op.alter_column("documents", "file_size", nullable=True)


def downgrade() -> None:
    op.alter_column("documents", "file_size", nullable=False)
    op.alter_column("documents", "mime_type", nullable=False)
    op.alter_column("documents", "file_hash", nullable=False)
    op.alter_column("documents", "file_path", nullable=False)
    op.drop_column("documents", "is_manual")
    op.drop_column("documents", "is_paid")
