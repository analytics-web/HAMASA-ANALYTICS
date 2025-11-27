from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


"""createed table project_progress and linked its relationship with project table

Revision ID: 0699d75cc1f6
Revises: 282f75db8540
Create Date: 2025-11-26 13:50:26.753137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0699d75cc1f6'
down_revision: Union[str, Sequence[str], None] = '282f75db8540'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # existing enum in DB
    project_status_enum = postgresql.ENUM(
        "draft",
        "submitted",
        "review",
        "in_progress",
        "active",
        "completed",
        "archived",
        name="projectstatus",
        create_type=False,   # DO NOT create again
    )

    # bind enum to connection (important)
    bind = op.get_bind()
    project_status_enum.create(bind, checkfirst=True)

    # create table
    op.create_table(
        "project_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_no", sa.Integer(), nullable=False),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hamasa_users.id"),
            nullable=False,
        ),
        sa.Column("previous_status", project_status_enum, nullable=True),
        sa.Column("current_status", project_status_enum, nullable=False),
        sa.Column("action", sa.String(255)),
        sa.Column("comment", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
