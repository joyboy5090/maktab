"""add_teacher_unavailable_slots

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-11-26 00:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unavailable_slots JSONB column to teachers table."""
    op.add_column(
        'teachers',
        sa.Column('unavailable_slots', postgresql.JSONB(), server_default='[]', nullable=False)
    )


def downgrade() -> None:
    """Remove unavailable_slots column from teachers table."""
    op.drop_column('teachers', 'unavailable_slots')
