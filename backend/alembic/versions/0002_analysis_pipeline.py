"""Revision 0002: analysis pipeline tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_analysis_pipeline"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("toolchain_profile_id", sa.String(length=64), nullable=False),
        sa.Column("compile_commands_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("base_run_id", sa.Uuid(), nullable=True),
        sa.Column("files_total", sa.Integer(), nullable=False),
        sa.Column("files_parsed", sa.Integer(), nullable=False),
        sa.Column("files_failed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["base_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_runs_project_id", "analysis_runs", ["project_id"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])

    op.create_table(
        "file_index",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("absolute_path", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("include_edges_json", sa.JSON(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_index_project_id", "file_index", ["project_id"])

    op.create_table(
        "translation_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("working_directory", sa.Text(), nullable=False),
        sa.Column("compile_flags_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("translation_unit_hash", sa.String(length=64), nullable=True),
        sa.Column("ast_cache_path", sa.Text(), nullable=True),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("parse_duration_ms", sa.Integer(), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=True),
        sa.Column("preprocessor_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_translation_units_analysis_run_id", "translation_units", ["analysis_run_id"])

    op.create_table(
        "incremental_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("changed_files_json", sa.JSON(), nullable=False),
        sa.Column("affected_translation_units_json", sa.JSON(), nullable=False),
        sa.Column("cache_hits", sa.Integer(), nullable=False),
        sa.Column("cache_misses", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id"),
    )


def downgrade() -> None:
    op.drop_table("incremental_manifests")
    op.drop_index("ix_translation_units_analysis_run_id", table_name="translation_units")
    op.drop_table("translation_units")
    op.drop_index("ix_file_index_project_id", table_name="file_index")
    op.drop_table("file_index")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_project_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_table("projects")
