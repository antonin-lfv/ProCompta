"""add notifications table

Revision ID: 20260425_0006
Revises: 20260425_0005
Create Date: 2026-04-25
"""
from alembic import op

revision = "20260425_0006"
down_revision = "20260425_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtypeenum AS ENUM ('incomplete_document');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            type notificationtypeenum NOT NULL DEFAULT 'incomplete_document',
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            body TEXT,
            read BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_document_id ON notifications(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_read ON notifications(read)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications")
    op.execute("DROP TYPE IF EXISTS notificationtypeenum")
