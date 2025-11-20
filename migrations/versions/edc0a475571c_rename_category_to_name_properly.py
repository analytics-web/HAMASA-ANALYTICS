"""Rename category to name properly

Revision ID: edc0a475571c
Revises: 8fb29d0f9f29
Create Date: 2025-11-20 14:49:29.538849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edc0a475571c'
down_revision: Union[str, Sequence[str], None] = '8fb29d0f9f29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade() -> None:
    # 1. Add nullable name column
    op.add_column(
        "project_categories",
        sa.Column("name", sa.String(), nullable=True)
    )

    # 2. Copy category → name
    op.execute("""
        UPDATE project_categories
        SET name = category
        WHERE name IS NULL
    """)

    # 3. Make name NOT NULL
    op.alter_column(
        "project_categories",
        "name",
        nullable=False
    )

    # 4. Drop old column
    op.drop_column("project_categories", "category")


def downgrade() -> None:
    op.add_column(
        "project_categories",
        sa.Column("category", sa.String(), nullable=True)
    )

    op.execute("""
        UPDATE project_categories
        SET category = name
    """)

    op.drop_column("project_categories", "name")