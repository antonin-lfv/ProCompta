"""add users table

Revision ID: 20260425_0008
Revises: 20260425_0007
Create Date: 2026-04-25
"""
from alembic import op

revision = "20260425_0008"
down_revision = "20260425_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            default_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
            fiscal_year_start INTEGER NOT NULL DEFAULT 1,
            backup_path TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users")
