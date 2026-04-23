"""add category to documents

Revision ID: 20260423_0002
Revises: 20260422_0001
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260423_0002"
down_revision = "0001"
branch_labels = None
depends_on = None

category_enum = sa.Enum("depense", "recette", "autre", name="categoryenum")


def upgrade() -> None:
    category_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "documents",
        sa.Column(
            "category",
            sa.Enum("depense", "recette", "autre", name="categoryenum"),
            nullable=False,
            server_default="autre",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "category")
    category_enum.drop(op.get_bind(), checkfirst=True)
