"""add gender column to user

Revision ID: fad1dc847283
Revises: e8356dfc215d
Create Date: 2025-09-30 14:25:33.233975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fad1dc847283'
down_revision: Union[str, Sequence[str], None] = 'e8356dfc215d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the gender ENUM type
    op.execute("CREATE TYPE gender AS ENUM ('male', 'female', 'other')")
    # Add the gender column
    op.add_column('users', sa.Column('gender', postgresql.ENUM('male', 'female', 'other', name='gender'), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    # Drop the gender column
    op.drop_column('users', 'gender')
    # Drop the gender ENUM type
    op.execute("DROP TYPE IF EXISTS gender")
