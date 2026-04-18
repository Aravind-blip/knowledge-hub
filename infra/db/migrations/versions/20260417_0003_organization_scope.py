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
CORE_TABLES = ("documents", "document_chunks", "chat_sessions", "chat_messages", "ingestion_jobs")


def _has_foreign_key(inspector, table_name: str, constrained_column: str, referred_table: str) -> bool:
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("referred_table") != referred_table:
            continue
        if constrained_column in foreign_key.get("constrained_columns", []):
            return True
    return False


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_organizations_slug UNIQUE (slug)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_organizations_created_at ON organizations (created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_members (
            id UUID NOT NULL,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            role VARCHAR(20) DEFAULT 'member' NOT NULL,
            joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_organization_members_org_user UNIQUE (organization_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_organization_members_user_id ON organization_members (user_id)")

    for table_name in CORE_TABLES:
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS organization_id UUID")

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug)
            SELECT :organization_id, 'Demo Workspace', 'demo-workspace'
            WHERE NOT EXISTS (
                SELECT 1 FROM organizations
                WHERE id = :organization_id OR slug = 'demo-workspace'
            )
            """
        ).bindparams(sa.bindparam("organization_id", value=DEMO_ORG_ID, type_=UUID(as_uuid=True)))
    )

    for table_name in CORE_TABLES:
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
                SELECT :id, :organization_id, :user_id, :role
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM organization_members
                    WHERE organization_id = :organization_id AND user_id = :user_id
                )
                """
            ).bindparams(
                id=uuid.uuid4(),
                organization_id=DEMO_ORG_ID,
                user_id=row.user_id,
                role=role,
            )
        )

    for table_name in CORE_TABLES:
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN organization_id SET NOT NULL")

    inspector = sa.inspect(connection)
    foreign_keys = {
        "documents": "fk_documents_organization_id_organizations",
        "document_chunks": "fk_document_chunks_organization_id_organizations",
        "chat_sessions": "fk_chat_sessions_organization_id_organizations",
        "chat_messages": "fk_chat_messages_organization_id_organizations",
        "ingestion_jobs": "fk_ingestion_jobs_organization_id_organizations",
    }
    for table_name, constraint_name in foreign_keys.items():
        if not _has_foreign_key(inspector, table_name, "organization_id", "organizations"):
            op.create_foreign_key(
                constraint_name,
                table_name,
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_org_id_created_at ON documents (organization_id, created_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_org_id_status_created_at ON documents (organization_id, status, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_org_id_document_id ON document_chunks (organization_id, document_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_org_id_updated_at ON chat_sessions (organization_id, updated_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_sessions_org_id_user_id_updated_at ON chat_sessions (organization_id, user_id, updated_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_messages_org_id_session_id_created_at ON chat_messages (organization_id, session_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ingestion_jobs_org_id_created_at ON ingestion_jobs (organization_id, created_at)"
    )

    for table_name in CORE_TABLES:
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
