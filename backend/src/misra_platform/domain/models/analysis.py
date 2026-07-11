import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from misra_platform.repositories.base import Base

if TYPE_CHECKING:
    from misra_platform.domain.models.violations import ViolationRecord


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    toolchain_profile_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="clang-host"
    )
    compile_commands_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="project")
    file_index_entries: Mapped[list["FileIndexEntry"]] = relationship(back_populates="project")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    run_type: Mapped[str] = mapped_column(String(32), nullable=False, default="full")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    base_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )
    files_total: Mapped[int] = mapped_column(Integer, default=0)
    files_parsed: Mapped[int] = mapped_column(Integer, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    project: Mapped[Project] = relationship(back_populates="analysis_runs")
    translation_units: Mapped[list["TranslationUnitRecord"]] = relationship(
        back_populates="analysis_run"
    )
    violations: Mapped[list["ViolationRecord"]] = relationship(back_populates="analysis_run")


class FileIndexEntry(Base):
    __tablename__ = "file_index"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    absolute_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    include_edges_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    project: Mapped[Project] = relationship(back_populates="file_index_entries")


class TranslationUnitRecord(Base):
    __tablename__ = "translation_units"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    working_directory: Mapped[str] = mapped_column(Text, nullable=False)
    compile_flags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    translation_unit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ast_cache_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    diagnostics_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preprocessor_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="translation_units")


class IncrementalManifest(Base):
    __tablename__ = "incremental_manifests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"),
        nullable=False,
        unique=True,
    )
    changed_files_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_translation_units_json: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0)
