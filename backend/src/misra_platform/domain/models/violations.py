import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from misra_platform.repositories.base import Base


class ViolationRecord(Base):
    __tablename__ = "violations"
    __table_args__ = (
        UniqueConstraint("analysis_run_id", "fingerprint", name="uq_violation_run_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=False,
        index=True,
    )
    translation_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("translation_units.id"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    column_start: Mapped[int] = mapped_column(Integer, nullable=False)
    column_end: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    offending_expression: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)
    source_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    ast_node_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    macro_expansion_chain_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggested_fix_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_factors_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    assigned_reviewer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    assigned_reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="violations")


class RuleExecutionMetricRecord(Base):
    __tablename__ = "rule_execution_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=False,
        index=True,
    )
    translation_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("translation_units.id"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class RuleRunStatisticsRecord(Base):
    __tablename__ = "rule_run_statistics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=False,
        unique=True,
    )
    rules_executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    violations_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    violations_deduplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    translation_units_analyzed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


from misra_platform.domain.models.analysis import AnalysisRun  # noqa: E402, F401
