"""Add user ownership and row-level security."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260409_0002"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("document_chunks", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("chat_sessions", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("chat_messages", sa.Column("user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("user_id", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_documents_user_id_created_at", "documents", ["user_id", "created_at"], unique=False)
    op.create_index("ix_document_chunks_user_id_document_id", "document_chunks", ["user_id", "document_id"], unique=False)
    op.create_index("ix_chat_sessions_user_id_updated_at", "chat_sessions", ["user_id", "updated_at"], unique=False)
    op.create_index("ix_chat_messages_user_id_session_id", "chat_messages", ["user_id", "session_id"], unique=False)
    op.create_index("ix_ingestion_jobs_user_id_created_at", "ingestion_jobs", ["user_id", "created_at"], unique=False)

    for table_name in ("documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs"):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY IF NOT EXISTS documents_owner_policy
        ON documents
        FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY IF NOT EXISTS document_chunks_owner_policy
        ON document_chunks
        FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY IF NOT EXISTS chat_sessions_owner_policy
        ON chat_sessions
        FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY IF NOT EXISTS chat_messages_owner_policy
        ON chat_messages
        FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )
    op.execute(
        """
        CREATE POLICY IF NOT EXISTS ingestion_jobs_owner_policy
        ON ingestion_jobs
        FOR ALL
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ingestion_jobs_owner_policy ON ingestion_jobs")
    op.execute("DROP POLICY IF EXISTS chat_messages_owner_policy ON chat_messages")
    op.execute("DROP POLICY IF EXISTS chat_sessions_owner_policy ON chat_sessions")
    op.execute("DROP POLICY IF EXISTS document_chunks_owner_policy ON document_chunks")
    op.execute("DROP POLICY IF EXISTS documents_owner_policy ON documents")

    op.drop_index("ix_ingestion_jobs_user_id_created_at", table_name="ingestion_jobs")
    op.drop_index("ix_chat_messages_user_id_session_id", table_name="chat_messages")
    op.drop_index("ix_chat_sessions_user_id_updated_at", table_name="chat_sessions")
    op.drop_index("ix_document_chunks_user_id_document_id", table_name="document_chunks")
    op.drop_index("ix_documents_user_id_created_at", table_name="documents")

    op.drop_column("ingestion_jobs", "user_id")
    op.drop_column("chat_messages", "user_id")
    op.drop_column("chat_sessions", "user_id")
    op.drop_column("document_chunks", "user_id")
    op.drop_column("documents", "user_id")
