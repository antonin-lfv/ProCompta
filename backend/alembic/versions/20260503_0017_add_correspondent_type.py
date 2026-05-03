"""Add type enum to correspondents

Revision ID: 20260503_0017
Revises: 20260503_0016
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260503_0017"
down_revision = "20260503_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    correspondent_type = sa.Enum("client", "fournisseur", "les_deux", name="correspondenttype")
    correspondent_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "correspondents",
        sa.Column("type", sa.Enum("client", "fournisseur", "les_deux", name="correspondenttype"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("correspondents", "type")
    sa.Enum(name="correspondenttype").drop(op.get_bind(), checkfirst=True)
