"""Restore missing migration stub

Revision ID: 8fb29d0f9f29
Revises: ae6aa4101763
Create Date: 2025-11-20 11:52:24.903803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fb29d0f9f29'
down_revision: Union[str, Sequence[str], None] = 'ae6aa4101763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    pass

def downgrade():
    pass

