"""rename gmail tag to auto

Revision ID: 20260502_0012
Revises: 20260502_0011
Create Date: 2026-05-02
"""
from alembic import op

revision = "20260502_0012"
down_revision = "20260502_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE tags SET name = 'Auto', slug = 'auto'
        WHERE slug = 'gmail'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE tags SET name = 'Gmail', slug = 'gmail'
        WHERE slug = 'auto' AND name = 'Auto'
    """)
