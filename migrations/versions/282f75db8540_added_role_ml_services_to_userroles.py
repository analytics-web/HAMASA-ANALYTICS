"""added role ml_services to userroles

Revision ID: 282f75db8540
Revises: 4c0c6c30c81a
Create Date: 2025-11-26 10:20:19.903538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '282f75db8540'
down_revision: Union[str, Sequence[str], None] = '4c0c6c30c81a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add new role to the enum type
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ml_service';")


def downgrade():
    # PostgreSQL does not support removing enum values.
    # You must recreate the type if you need downgrade support.
    raise RuntimeError("Downgrade not supported for enum alteration.")