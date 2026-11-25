"""enable_rls_and_app_role

Revision ID: f4a9c2d1b8e0
Revises: e967abdda4dc
Create Date: 2026-11-26 00:08:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f4a9c2d1b8e0'
down_revision: Union[str, Sequence[str], None] = 'e967abdda4dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = [
    "subscriptions",
    "users",
    "teachers",
    "teacher_availabilities",
    "rooms",
    "classes",
    "subjects",
    "class_subject_allocations",
    "time_slots",
    "timetable_entries",
    "audit_logs",
]


def upgrade() -> None:
    """Enable Row-Level Security (RLS) on all tenant tables and configure non-owner maktab_app role."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'maktab_app') THEN
                CREATE ROLE maktab_app WITH LOGIN PASSWORD 'maktab_app_secret'
                    NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO maktab_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO maktab_app;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO maktab_app;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO maktab_app;"
    )

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_setting('app.is_super_admin', true) = 'on'
                OR school_id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
            )
            WITH CHECK (
                current_setting('app.is_super_admin', true) = 'on'
                OR school_id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
            );
            """
        )


def downgrade() -> None:
    """Disable RLS and remove tenant_isolation policies."""
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
