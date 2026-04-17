"""Add organization-scoped tenancy and policies."""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260417_0003"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None

DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_created_at", "organizations", ["created_at"], unique=False)

    op.create_table(
        "organization_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"], unique=False)

    op.add_column("documents", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
    op.add_column("document_chunks", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
    op.add_column("chat_sessions", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
    op.add_column("chat_messages", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug)
            VALUES (:organization_id, 'Demo Workspace', 'demo-workspace')
            """
        ).bindparams(sa.bindparam("organization_id", value=DEMO_ORG_ID, type_=UUID(as_uuid=True)))
    )

    for table_name in ("documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs"):
        op.execute(
            sa.text(f"UPDATE {table_name} SET organization_id = :organization_id WHERE organization_id IS NULL").bindparams(
                sa.bindparam("organization_id", value=DEMO_ORG_ID, type_=UUID(as_uuid=True))
            )
        )

    connection = op.get_bind()
    user_rows = connection.execute(
        sa.text(
            """
            SELECT DISTINCT user_id
            FROM (
                SELECT user_id FROM documents WHERE user_id IS NOT NULL
                UNION
                SELECT user_id FROM chat_sessions WHERE user_id IS NOT NULL
                UNION
                SELECT user_id FROM chat_messages WHERE user_id IS NOT NULL
                UNION
                SELECT user_id FROM ingestion_jobs WHERE user_id IS NOT NULL
                UNION
                SELECT CAST(:demo_user_id AS uuid) AS user_id
            ) AS scoped_users
            """
        ).bindparams(demo_user_id=DEMO_USER_ID)
    )
    for row in user_rows:
        role = "admin" if str(row.user_id) == DEMO_USER_ID else "member"
        connection.execute(
            sa.text(
                """
                INSERT INTO organization_members (id, organization_id, user_id, role)
                VALUES (:id, :organization_id, :user_id, :role)
                ON CONFLICT ON CONSTRAINT uq_organization_members_org_user DO NOTHING
                """
            ).bindparams(
                id=uuid.uuid4(),
                organization_id=DEMO_ORG_ID,
                user_id=row.user_id,
                role=role,
            )
        )

    op.alter_column("documents", "organization_id", nullable=False)
    op.alter_column("document_chunks", "organization_id", nullable=False)
    op.alter_column("chat_sessions", "organization_id", nullable=False)
    op.alter_column("chat_messages", "organization_id", nullable=False)
    op.alter_column("ingestion_jobs", "organization_id", nullable=False)

    op.create_foreign_key(
        "fk_documents_organization_id_organizations",
        "documents",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_document_chunks_organization_id_organizations",
        "document_chunks",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_chat_sessions_organization_id_organizations",
        "chat_sessions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_chat_messages_organization_id_organizations",
        "chat_messages",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_ingestion_jobs_organization_id_organizations",
        "ingestion_jobs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index("ix_documents_org_id_created_at", "documents", ["organization_id", "created_at"], unique=False)
    op.create_index(
        "ix_documents_org_id_status_created_at",
        "documents",
        ["organization_id", "status", "created_at"],
        unique=False,
    )
    op.create_index("ix_document_chunks_org_id_document_id", "document_chunks", ["organization_id", "document_id"], unique=False)
    op.create_index("ix_chat_sessions_org_id_updated_at", "chat_sessions", ["organization_id", "updated_at"], unique=False)
    op.create_index(
        "ix_chat_sessions_org_id_user_id_updated_at",
        "chat_sessions",
        ["organization_id", "user_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_org_id_session_id_created_at",
        "chat_messages",
        ["organization_id", "session_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_ingestion_jobs_org_id_created_at", "ingestion_jobs", ["organization_id", "created_at"], unique=False)

    for table_name in ("documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs"):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    policy_statements = [
        "DROP POLICY IF EXISTS documents_owner_policy ON documents",
        "DROP POLICY IF EXISTS document_chunks_owner_policy ON document_chunks",
        "DROP POLICY IF EXISTS chat_sessions_owner_policy ON chat_sessions",
        "DROP POLICY IF EXISTS chat_messages_owner_policy ON chat_messages",
        "DROP POLICY IF EXISTS ingestion_jobs_owner_policy ON ingestion_jobs",
        "DROP POLICY IF EXISTS documents_org_policy ON documents",
        """
        CREATE POLICY documents_org_policy
        ON documents
        FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        """,
        "DROP POLICY IF EXISTS document_chunks_org_policy ON document_chunks",
        """
        CREATE POLICY document_chunks_org_policy
        ON document_chunks
        FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        """,
        "DROP POLICY IF EXISTS chat_sessions_org_policy ON chat_sessions",
        """
        CREATE POLICY chat_sessions_org_policy
        ON chat_sessions
        FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        """,
        "DROP POLICY IF EXISTS chat_messages_org_policy ON chat_messages",
        """
        CREATE POLICY chat_messages_org_policy
        ON chat_messages
        FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        """,
        "DROP POLICY IF EXISTS ingestion_jobs_org_policy ON ingestion_jobs",
        """
        CREATE POLICY ingestion_jobs_org_policy
        ON ingestion_jobs
        FOR ALL
        USING (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid)
        """,
    ]
    for statement in policy_statements:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ingestion_jobs_org_policy ON ingestion_jobs")
    op.execute("DROP POLICY IF EXISTS chat_messages_org_policy ON chat_messages")
    op.execute("DROP POLICY IF EXISTS chat_sessions_org_policy ON chat_sessions")
    op.execute("DROP POLICY IF EXISTS document_chunks_org_policy ON document_chunks")
    op.execute("DROP POLICY IF EXISTS documents_org_policy ON documents")

    op.drop_index("ix_ingestion_jobs_org_id_created_at", table_name="ingestion_jobs")
    op.drop_index("ix_chat_messages_org_id_session_id_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_sessions_org_id_user_id_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_org_id_updated_at", table_name="chat_sessions")
    op.drop_index("ix_document_chunks_org_id_document_id", table_name="document_chunks")
    op.drop_index("ix_documents_org_id_status_created_at", table_name="documents")
    op.drop_index("ix_documents_org_id_created_at", table_name="documents")

    op.drop_constraint("fk_ingestion_jobs_organization_id_organizations", "ingestion_jobs", type_="foreignkey")
    op.drop_constraint("fk_chat_messages_organization_id_organizations", "chat_messages", type_="foreignkey")
    op.drop_constraint("fk_chat_sessions_organization_id_organizations", "chat_sessions", type_="foreignkey")
    op.drop_constraint("fk_document_chunks_organization_id_organizations", "document_chunks", type_="foreignkey")
    op.drop_constraint("fk_documents_organization_id_organizations", "documents", type_="foreignkey")

    op.drop_column("ingestion_jobs", "organization_id")
    op.drop_column("chat_messages", "organization_id")
    op.drop_column("chat_sessions", "organization_id")
    op.drop_column("document_chunks", "organization_id")
    op.drop_column("documents", "organization_id")

    op.drop_index("ix_organization_members_user_id", table_name="organization_members")
    op.drop_table("organization_members")
    op.drop_index("ix_organizations_created_at", table_name="organizations")
    op.drop_table("organizations")
