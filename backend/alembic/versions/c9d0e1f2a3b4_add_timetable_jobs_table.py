"""add_timetable_jobs_table

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-11-26 00:26:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create timetable_jobs table with RLS policy."""
    op.create_table(
        'timetable_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('school_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('term', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'running', 'done', 'failed')", name='ck_timetable_jobs_status'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_timetable_jobs_school_status', 'timetable_jobs', ['school_id', 'status'], unique=False)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE timetable_jobs TO maktab_app;")
    op.execute("ALTER TABLE timetable_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE timetable_jobs FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON timetable_jobs
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
    """Drop timetable_jobs table and RLS policy."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON timetable_jobs;")
    op.execute("ALTER TABLE timetable_jobs NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE timetable_jobs DISABLE ROW LEVEL SECURITY;")
    op.drop_index('idx_timetable_jobs_school_status', table_name='timetable_jobs')
    op.drop_table('timetable_jobs')
