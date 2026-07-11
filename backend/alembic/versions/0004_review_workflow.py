"""Revision 0004: human-in-the-loop review workflow tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_review_workflow"
down_revision: str | None = "0003_violations_and_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "violations", sa.Column("assigned_reviewer_id", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "violations", sa.Column("assigned_reviewer_name", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_violations_assigned_reviewer_id", "violations", ["assigned_reviewer_id"]
    )

    op.create_table(
        "violation_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("violation_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=False),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("edited_fix_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["violation_id"], ["violations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_violation_reviews_violation_id", "violation_reviews", ["violation_id"])
    op.create_index("ix_violation_reviews_action", "violation_reviews", ["action"])
    op.create_index("ix_violation_reviews_reviewer_id", "violation_reviews", ["reviewer_id"])
    op.create_index(
        "ix_violation_reviews_violation_created", "violation_reviews", ["violation_id", "created_at"]
    )

    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_name", sa.String(length=255), nullable=True),
        sa.Column("old_state_json", sa.JSON(), nullable=True),
        sa.Column("new_state_json", sa.JSON(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_entries_entity_type", "audit_entries", ["entity_type"])
    op.create_index("ix_audit_entries_entity_id", "audit_entries", ["entity_id"])
    op.create_index("ix_audit_entries_action", "audit_entries", ["action"])
    op.create_index("ix_audit_entries_actor_id", "audit_entries", ["actor_id"])
    op.create_index("ix_audit_entries_entity", "audit_entries", ["entity_type", "entity_id"])

    op.create_table(
        "patches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("violation_id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("unified_diff", sa.Text(), nullable=False),
        sa.Column("git_patch", sa.Text(), nullable=False),
        sa.Column("source_available", sa.Boolean(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exported_by", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["violation_id"], ["violations.id"]),
        sa.ForeignKeyConstraint(["review_id"], ["violation_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patches_violation_id", "patches", ["violation_id"])
    op.create_index("ix_patches_review_id", "patches", ["review_id"])
    op.create_index("ix_patches_status", "patches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_patches_status", table_name="patches")
    op.drop_index("ix_patches_review_id", table_name="patches")
    op.drop_index("ix_patches_violation_id", table_name="patches")
    op.drop_table("patches")

    op.drop_index("ix_audit_entries_entity", table_name="audit_entries")
    op.drop_index("ix_audit_entries_actor_id", table_name="audit_entries")
    op.drop_index("ix_audit_entries_action", table_name="audit_entries")
    op.drop_index("ix_audit_entries_entity_id", table_name="audit_entries")
    op.drop_index("ix_audit_entries_entity_type", table_name="audit_entries")
    op.drop_table("audit_entries")

    op.drop_index("ix_violation_reviews_violation_created", table_name="violation_reviews")
    op.drop_index("ix_violation_reviews_reviewer_id", table_name="violation_reviews")
    op.drop_index("ix_violation_reviews_action", table_name="violation_reviews")
    op.drop_index("ix_violation_reviews_violation_id", table_name="violation_reviews")
    op.drop_table("violation_reviews")

    op.drop_index("ix_violations_assigned_reviewer_id", table_name="violations")
    op.drop_column("violations", "assigned_reviewer_name")
    op.drop_column("violations", "assigned_reviewer_id")
