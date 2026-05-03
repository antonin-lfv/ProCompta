"""Drop unused backup_path column from users

Revision ID: 20260503_0018
Revises: 20260503_0017
Create Date: 2026-05-03
"""
from alembic import op

revision = "20260503_0018"
down_revision = "20260503_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "backup_path")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column("users", sa.Column("backup_path", sa.Text(), nullable=True))
