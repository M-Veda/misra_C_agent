"""Revision 0005: enterprise teams, compliance snapshots, integration configs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_enterprise"
down_revision: str | None = "0004_review_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])

    op.create_table(
        "compliance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column("violations_total", sa.Integer(), nullable=False),
        sa.Column("violations_open", sa.Integer(), nullable=False),
        sa.Column("violations_resolved", sa.Integer(), nullable=False),
        sa.Column("rules_executed", sa.Integer(), nullable=False),
        sa.Column("compliance_score", sa.Float(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id"),
    )
    op.create_index("ix_compliance_snapshots_project_id", "compliance_snapshots", ["project_id"])
    op.create_index("ix_compliance_snapshots_team_id", "compliance_snapshots", ["team_id"])
    op.create_index("ix_compliance_snapshots_captured_at", "compliance_snapshots", ["captured_at"])

    op.create_table(
        "integration_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_configs_project_id", "integration_configs", ["project_id"])
    op.create_index("ix_integration_configs_provider", "integration_configs", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_integration_configs_provider", table_name="integration_configs")
    op.drop_index("ix_integration_configs_project_id", table_name="integration_configs")
    op.drop_table("integration_configs")
    op.drop_index("ix_compliance_snapshots_captured_at", table_name="compliance_snapshots")
    op.drop_index("ix_compliance_snapshots_team_id", table_name="compliance_snapshots")
    op.drop_index("ix_compliance_snapshots_project_id", table_name="compliance_snapshots")
    op.drop_table("compliance_snapshots")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_table("teams")
