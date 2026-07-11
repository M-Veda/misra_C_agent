"""Revision 0003: violations and rule execution tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_violations_and_rules"
down_revision: str | None = "0002_analysis_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "violations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("translation_unit_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("column_start", sa.Integer(), nullable=False),
        sa.Column("column_end", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("offending_expression", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("risk_description", sa.Text(), nullable=False),
        sa.Column("source_snippet", sa.Text(), nullable=False),
        sa.Column("ast_node_reference", sa.String(length=128), nullable=False),
        sa.Column("macro_expansion_chain_json", sa.JSON(), nullable=True),
        sa.Column("suggested_fix_json", sa.JSON(), nullable=True),
        sa.Column("confidence_factors_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["translation_unit_id"], ["translation_units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "fingerprint", name="uq_violation_run_fingerprint"),
    )
    op.create_index("ix_violations_analysis_run_id", "violations", ["analysis_run_id"])
    op.create_index("ix_violations_translation_unit_id", "violations", ["translation_unit_id"])
    op.create_index("ix_violations_project_id", "violations", ["project_id"])
    op.create_index("ix_violations_rule_id", "violations", ["rule_id"])
    op.create_index("ix_violations_fingerprint", "violations", ["fingerprint"])
    op.create_index("ix_violations_status", "violations", ["status"])

    op.create_table(
        "rule_execution_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("translation_unit_id", sa.Uuid(), nullable=True),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("violation_count", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.ForeignKeyConstraint(["translation_unit_id"], ["translation_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rule_execution_metrics_analysis_run_id", "rule_execution_metrics", ["analysis_run_id"]
    )
    op.create_index(
        "ix_rule_execution_metrics_translation_unit_id",
        "rule_execution_metrics",
        ["translation_unit_id"],
    )
    op.create_index("ix_rule_execution_metrics_rule_id", "rule_execution_metrics", ["rule_id"])

    op.create_table(
        "rule_run_statistics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("rules_executed", sa.Integer(), nullable=False),
        sa.Column("violations_total", sa.Integer(), nullable=False),
        sa.Column("violations_deduplicated", sa.Integer(), nullable=False),
        sa.Column("execution_duration_ms", sa.Float(), nullable=False),
        sa.Column("translation_units_analyzed", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id"),
    )


def downgrade() -> None:
    op.drop_table("rule_run_statistics")
    op.drop_index("ix_rule_execution_metrics_rule_id", table_name="rule_execution_metrics")
    op.drop_index(
        "ix_rule_execution_metrics_translation_unit_id", table_name="rule_execution_metrics"
    )
    op.drop_index("ix_rule_execution_metrics_analysis_run_id", table_name="rule_execution_metrics")
    op.drop_table("rule_execution_metrics")
    op.drop_index("ix_violations_status", table_name="violations")
    op.drop_index("ix_violations_fingerprint", table_name="violations")
    op.drop_index("ix_violations_rule_id", table_name="violations")
    op.drop_index("ix_violations_project_id", table_name="violations")
    op.drop_index("ix_violations_translation_unit_id", table_name="violations")
    op.drop_index("ix_violations_analysis_run_id", table_name="violations")
    op.drop_table("violations")
