"""init

Revision ID: 0001
Revises:
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "correspondents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "document_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("color", sa.String(), nullable=False, server_default="#6366f1"),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("color", sa.String(), nullable=False, server_default="#10b981"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("amount_ht", sa.Numeric(12, 2), nullable=True),
        sa.Column("vat_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True, server_default="0.00"),
        sa.Column("amount_ttc", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "correspondent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("correspondents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "document_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "document_tags",
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_index("ix_documents_document_date", "documents", ["document_date"])
    op.create_index("ix_documents_correspondent_id", "documents", ["correspondent_id"])
    op.create_index("ix_documents_document_type_id", "documents", ["document_type_id"])


def downgrade() -> None:
    op.drop_table("document_tags")
    op.drop_index("ix_documents_document_type_id", table_name="documents")
    op.drop_index("ix_documents_correspondent_id", table_name="documents")
    op.drop_index("ix_documents_document_date", table_name="documents")
    op.drop_table("documents")
    op.drop_table("tags")
    op.drop_table("document_types")
    op.drop_table("correspondents")
