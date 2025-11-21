"""added timestamps to table client_users

Revision ID: 4c0c6c30c81a
Revises: edc0a475571c
Create Date: 2025-11-21 15:37:50.651491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c0c6c30c81a'
down_revision: Union[str, Sequence[str], None] = 'edc0a475571c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        'client_users', 
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'client_users', 
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('client_users', 'updated_at')
    op.drop_column('client_users', 'created_at')
