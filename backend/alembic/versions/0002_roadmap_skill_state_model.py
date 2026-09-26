"""Add roadmap skill state and classification tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep legacy roadmap columns for compatibility while the roadmap module is migrating.
    op.add_column("roadmaps", sa.Column("title", sa.String(length=200), nullable=True))
    op.add_column("roadmaps", sa.Column("summary", sa.Text(), nullable=True))
    op.alter_column("roadmaps", "analysis_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    op.create_table(
        "roadmap_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "classification",
            sa.Enum("missing", "partial", name="roadmapskillclassification"),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.Enum(
                "locked",
                "unlocked",
                "learning",
                "learning_completed",
                "mini_project_available",
                "project_in_progress",
                "project_submitted",
                "assessment_available",
                "assessment_started",
                "verified",
                "targeted_review",
                "retake_available",
                name="roadmapskillstate",
            ),
            nullable=False,
            server_default="locked",
        ),
        sa.Column("learning_track", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("mini_project", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("assessment", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("prerequisites", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("dependencies", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["roadmap_id"], ["roadmaps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roadmap_skills_roadmap_id", "roadmap_skills", ["roadmap_id"])
    op.create_index("ix_roadmap_skills_name", "roadmap_skills", ["name"])
    op.create_index(
        "ix_roadmap_skills_classification",
        "roadmap_skills",
        ["classification"],
    )
    op.create_index("ix_roadmap_skills_state", "roadmap_skills", ["state"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_skills_state", table_name="roadmap_skills")
    op.drop_index("ix_roadmap_skills_classification", table_name="roadmap_skills")
    op.drop_index("ix_roadmap_skills_name", table_name="roadmap_skills")
    op.drop_index("ix_roadmap_skills_roadmap_id", table_name="roadmap_skills")
    op.drop_table("roadmap_skills")
    op.drop_column("roadmaps", "title")
    op.drop_column("roadmaps", "summary")
