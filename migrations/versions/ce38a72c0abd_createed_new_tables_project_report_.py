"""created new tables project_report project_report_progress and project_progress

Revision ID: ce38a72c0abd
Revises: 0699d75cc1f6
Create Date: 2025-11-27 11:01:19.505468
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from typing import Sequence, Union


# revision identifiers
revision: str = 'ce38a72c0abd'
down_revision: Union[str, Sequence[str], None] = '0699d75cc1f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. Register enum without creating it (it already exists)
    # ----------------------------------------------------------------
    project_report_status = postgresql.ENUM(
        'Unverified',
        'Verified',
        'Rejected',
        name='projectreportstatus',
        create_type=False   # <--- IMPORTANT
    )

    # ----------------------------------------------------------------
    # 2. project_report table
    # ----------------------------------------------------------------
    op.create_table(
        'project_report',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'),
                  nullable=False),

        sa.Column('publication_date', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text),
        sa.Column('source', sa.String(255)),
        sa.Column('media_category', sa.String(255)),
        sa.Column('media_format', sa.String(50)),

        sa.Column('thematic_area', sa.String(255)),
        sa.Column('thematic_description', sa.Text),
        sa.Column('objectives', postgresql.JSONB),
        sa.Column('link', sa.Text),

        sa.Column('status', sa.Enum(
            'Unverified', 'Verified', 'Rejected',
            name='projectreportstatus'
        )),

        sa.Column('extra_metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    # ----------------------------------------------------------------
    # 3. project_report_progress table
    # ----------------------------------------------------------------
    op.create_table(
        'project_report_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('stage_no', sa.Integer(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('hamasa_users.id'),
                  nullable=False),

        sa.Column('previous_status', sa.Enum(
            'Unverified', 'Verified', 'Rejected',
            name='projectreportstatus'
        )),
        sa.Column('current_status', sa.Enum(
            'Unverified', 'Verified', 'Rejected',
            name='projectreportstatus'
        ), nullable=False),

        sa.Column('action', sa.String(255)),
        sa.Column('comment', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )

    # ----------------------------------------------------------------
    # 4. project_progress table (uses existing projectstatus enum)
    # ----------------------------------------------------------------
    project_status_enum = postgresql.ENUM(
        'draft',
        'submitted',
        'review',
        'in_progress',
        'active',
        'completed',
        'archived',
        name='projectstatus',
        create_type=False,       # Do NOT recreate
    )

    op.create_table(
        'project_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
              sa.ForeignKey('projects.id', ondelete='CASCADE'),
              nullable=False),

        sa.Column('stage_no', sa.Integer(), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True),
              sa.ForeignKey('hamasa_users.id'),
              nullable=False),

    # FIXED ENUM COLUMNS
        sa.Column('previous_status', project_status_enum, nullable=True),
        sa.Column('current_status', project_status_enum, nullable=False),

        sa.Column('action', sa.String(255)),
        sa.Column('comment', sa.Text),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('project_progress')
    op.drop_table('project_report_progress')
    op.drop_table('project_report')

    # DO NOT DROP TYPE (it may be used elsewhere)
    # op.execute("DROP TYPE IF EXISTS projectreportstatus")
