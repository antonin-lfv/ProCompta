"""add document_activity table

Revision ID: 20260425_0007
Revises: 20260425_0006
Create Date: 2026-04-25
"""
from alembic import op

revision = "20260425_0007"
down_revision = "20260425_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE activityeventenum AS ENUM (
                'uploaded', 'title_changed', 'correspondent_changed', 'type_changed',
                'category_changed', 'amount_changed', 'date_changed', 'notes_changed',
                'archived', 'unarchived'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_activity (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            event_type activityeventenum NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_activity_document_id ON document_activity(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_activity_created_at ON document_activity(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_activity")
    op.execute("DROP TYPE IF EXISTS activityeventenum")
