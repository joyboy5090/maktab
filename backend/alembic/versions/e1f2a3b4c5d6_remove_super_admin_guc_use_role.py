"""remove_super_admin_guc_use_role

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-26 10:25:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
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
    "timetable_jobs",
]


def upgrade() -> None:
    """Remove app.is_super_admin GUC bypass from RLS policies; allow only non-maktab_app (owner/maktab_super) roles."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'maktab_super') THEN
                CREATE ROLE maktab_super NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
            END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO maktab_super;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO maktab_super;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO maktab_super;")

    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_user <> 'maktab_app'
                OR school_id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
            )
            WITH CHECK (
                current_user <> 'maktab_app'
                OR school_id = NULLIF(current_setting('app.current_school_id', true), '')::uuid
            );
            """
        )


def downgrade() -> None:
    """Restore previous GUC-based RLS policies."""
    for table in reversed(TENANT_TABLES):
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
