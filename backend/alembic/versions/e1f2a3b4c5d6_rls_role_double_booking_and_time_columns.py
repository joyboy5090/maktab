"""rls_role_double_booking_and_time_columns

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-11-26 09:08:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
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
    """Update RLS policies for app.current_role, add double-booking constraints, and use TIME for time_slots."""
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                current_setting('app.current_role', true) = 'SUPER_ADMIN'
                OR current_setting('app.is_super_admin', true) = 'on'
                OR school_id::text = current_setting('app.current_school_id', true)
            )
            WITH CHECK (
                current_setting('app.current_role', true) = 'SUPER_ADMIN'
                OR current_setting('app.is_super_admin', true) = 'on'
                OR school_id::text = current_setting('app.current_school_id', true)
            );
            """
        )

    op.create_unique_constraint(
        'uq_teacher_slot_term',
        'timetable_entries',
        ['school_id', 'term', 'day', 'lesson_order', 'teacher_id'],
    )
    op.create_index(
        'uq_room_slot_term',
        'timetable_entries',
        ['school_id', 'term', 'day', 'lesson_order', 'room_id'],
        unique=True,
        postgresql_where=sa.text('room_id IS NOT NULL'),
    )

    op.execute(
        "ALTER TABLE time_slots "
        "ALTER COLUMN start_time TYPE TIME USING start_time::time, "
        "ALTER COLUMN end_time TYPE TIME USING end_time::time;"
    )


def downgrade() -> None:
    """Revert time_slots columns, double-booking constraints, and RLS policies."""
    op.execute(
        "ALTER TABLE time_slots "
        "ALTER COLUMN start_time TYPE VARCHAR(20) USING start_time::text, "
        "ALTER COLUMN end_time TYPE VARCHAR(20) USING end_time::text;"
    )

    op.drop_index('uq_room_slot_term', table_name='timetable_entries')
    op.drop_constraint('uq_teacher_slot_term', 'timetable_entries', type_='unique')

    for table in TENANT_TABLES:
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
