"""made monitoring objective a JSONB in table thematic areas

Revision ID: 6a02ac3e58d4
Revises: d44e505ec078
Create Date: 2025-11-19 18:05:51.352172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6a02ac3e58d4'
down_revision: Union[str, Sequence[str], None] = 'd44e505ec078'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "project_thematic_areas",
        "monitoring_objective",
        type_=postgresql.JSONB(),
        postgresql_using="to_jsonb(monitoring_objective)"

    )

def downgrade():
    op.alter_column(
        "project_thematic_areas",
        "monitoring_objective",
        type_=sa.String(),
        postgresql_using="monitoring_objective::text"
    )