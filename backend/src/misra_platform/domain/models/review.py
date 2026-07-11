"""Human-in-the-loop review workflow models.

All tables in this module are append-only. Rows are never updated or deleted
after creation; every engineer action produces a brand-new row so that the
full review history remains reconstructable and auditable.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from misra_platform.repositories.base import Base


class ViolationReviewRecord(Base):
    """Append-only history of every review action taken on a violation."""

    __tablename__ = "violation_reviews"
    __table_args__ = (Index("ix_violation_reviews_violation_created", "violation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    violation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("violations.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_fix_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    violation: Mapped["ViolationRecord"] = relationship()  # noqa: F821


class AuditEntryRecord(Base):
    """Immutable, append-only audit log for every state-changing action."""

    __tablename__ = "audit_entries"
    __table_args__ = (Index("ix_audit_entries_entity", "entity_type", "entity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class PatchRecord(Base):
    """Generated, export-only patch artifacts. Never applied by the system."""

    __tablename__ = "patches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    violation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("violations.id"), nullable=False, index=True
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("violation_reviews.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    unified_diff: Mapped[str] = mapped_column(Text, nullable=False)
    git_patch: Mapped[str] = mapped_column(Text, nullable=False)
    source_available: Mapped[bool] = mapped_column(nullable=False, default=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated", index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
