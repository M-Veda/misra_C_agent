import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from misra_platform_rules.rule_context import PreviousViolation
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.config import Settings
from misra_platform.core.logging import get_logger
from misra_platform.domain.enums.analysis_status import (
    AnalysisRunType,
    AnalysisStatus,
    TranslationUnitStatus,
)
from misra_platform.domain.models.analysis import (
    AnalysisRun,
    FileIndexEntry,
    IncrementalManifest,
    Project,
    TranslationUnitRecord,
)
from misra_platform.integrations.clang_bridge.ast_client import ClangAstClient
from misra_platform.integrations.clang_bridge.compile_db_parser import load_compile_commands
from misra_platform.integrations.clang_bridge.incremental_index import (
    build_file_index,
    compute_affected_translation_units,
    compute_changed_files,
)
from misra_platform.integrations.storage.local import LocalArtifactStorage
from misra_platform.repositories.violation_repo import ViolationRepository
from misra_platform.services.rule_dispatcher import RuleDispatcher
from misra_platform.services.toolchain_profile_service import ToolchainProfileService

logger = get_logger(__name__)


class AnalysisOrchestrator:
    def __init__(self, settings: Settings, redis: Redis) -> None:
        self.settings = settings
        self.redis = redis
        self.storage = LocalArtifactStorage(settings)
        self.toolchains = ToolchainProfileService(settings)

    async def publish_event(
        self, run_id: uuid.UUID, event_type: str, payload: dict[str, Any]
    ) -> None:
        message = {
            "event_type": event_type,
            "analysis_run_id": str(run_id),
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        await self.redis.publish(f"analysis:{run_id}", json.dumps(message))

    async def run_analysis(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        run_type: AnalysisRunType = AnalysisRunType.FULL,
        base_run_id: uuid.UUID | None = None,
    ) -> None:
        run = await session.get(AnalysisRun, run_id)
        project = await session.get(Project, project_id)
        if not run or not project:
            return

        try:
            run.status = AnalysisStatus.RUNNING
            run.started_at = datetime.now(UTC)
            await session.commit()
            await self.publish_event(run_id, "analysis.started", {"project_id": str(project_id)})

            compile_commands_path = Path(project.compile_commands_path or "")
            validation = load_compile_commands(compile_commands_path)
            if not validation.is_valid:
                run.status = AnalysisStatus.FAILED
                run.error_message = "; ".join(validation.diagnostics)
                run.completed_at = datetime.now(UTC)
                await session.commit()
                await self.publish_event(
                    run_id,
                    "analysis.failed",
                    {"error": run.error_message},
                )
                return

            profile = self.toolchains.get_profile(project.toolchain_profile_id)
            target_triple = profile.get("target_triple", "") if profile else ""

            project_root = Path(project.root_path)
            source_files = [Path(entry.absolute_file) for entry in validation.entries]
            current_index = build_file_index(project_root, source_files)

            affected_files = {entry.absolute_file for entry in validation.entries}
            if run_type == AnalysisRunType.INCREMENTAL and base_run_id:
                previous_rows = await session.execute(
                    select(FileIndexEntry).where(FileIndexEntry.project_id == project_id)
                )
                previous_index = {
                    row.relative_path: row.content_hash for row in previous_rows.scalars().all()
                }
                changed = compute_changed_files(previous_index, current_index)
                include_graph = {
                    node.relative_path: node.include_edges for node in current_index.values()
                }
                tu_relative_paths = [
                    str(Path(entry.absolute_file).relative_to(project_root))
                    for entry in validation.entries
                ]
                affected_relative = compute_affected_translation_units(
                    changed,
                    include_graph,
                    tu_relative_paths,
                )
                affected_files = {
                    str((project_root / relative_path).resolve())
                    for relative_path in affected_relative
                }

            run.files_total = len(affected_files)
            await session.commit()

            clang_client = ClangAstClient(self.settings)
            parsed_count = 0
            failed_count = 0
            rule_dispatcher = RuleDispatcher(self.settings) if self.settings.rule_engine_enabled else None
            violation_repo = ViolationRepository(session)
            previous_rows = await violation_repo.get_previous_fingerprints(project_id)
            previous_violations = [
                PreviousViolation(
                    fingerprint=row["fingerprint"],
                    rule_id=row["rule_id"],
                    file_path=row["file_path"],
                    status="open",
                )
                for row in previous_rows
            ]
            include_graph = {
                node.relative_path: node.include_edges for node in current_index.values()
            }
            pending_rule_artifacts: list[dict] = []
            pending_rule_tu_ids: list[uuid.UUID] = []

            for entry in validation.entries:
                if entry.absolute_file not in affected_files:
                    continue

                tu_record = TranslationUnitRecord(
                    analysis_run_id=run_id,
                    file_path=entry.absolute_file,
                    working_directory=entry.directory,
                    compile_flags_json=entry.arguments,
                    status=TranslationUnitStatus.PARSING,
                )
                session.add(tu_record)
                await session.commit()
                await session.refresh(tu_record)

                await self.publish_event(
                    run_id,
                    "translation_unit.started",
                    {"translation_unit_id": str(tu_record.id), "file_path": entry.absolute_file},
                )

                parse_result = await clang_client.parse_translation_unit(
                    file_path=entry.absolute_file,
                    working_directory=entry.directory,
                    compile_flags=entry.arguments,
                    toolchain_profile_id=project.toolchain_profile_id,
                    target_triple=target_triple,
                )

                artifact_payload = {
                    "translation_unit_id": str(tu_record.id),
                    "file_path": entry.absolute_file,
                    "translation_unit_hash": parse_result.translation_unit_hash,
                    "nodes": parse_result.nodes,
                    "diagnostics": parse_result.diagnostics,
                    "preprocessor": parse_result.preprocessor,
                }
                artifact_path = self.storage.ast_cache_path(
                    str(project_id),
                    str(run_id),
                    str(tu_record.id),
                )
                self.storage.write_ast_artifact(artifact_path, artifact_payload)

                tu_record.translation_unit_hash = parse_result.translation_unit_hash
                tu_record.ast_cache_path = str(artifact_path)
                tu_record.node_count = len(parse_result.nodes)
                tu_record.parse_duration_ms = parse_result.parse_duration_ms
                tu_record.diagnostics_json = parse_result.diagnostics
                tu_record.preprocessor_json = parse_result.preprocessor

                if parse_result.success:
                    tu_record.status = TranslationUnitStatus.COMPLETED
                    parsed_count += 1
                    pending_rule_artifacts.append(artifact_payload)
                    pending_rule_tu_ids.append(tu_record.id)
                else:
                    tu_record.status = TranslationUnitStatus.FAILED
                    tu_record.error_message = parse_result.status_message
                    failed_count += 1

                run.files_parsed = parsed_count
                run.files_failed = failed_count
                await session.commit()

                await self.publish_event(
                    run_id,
                    "translation_unit.completed",
                    {
                        "translation_unit_id": str(tu_record.id),
                        "file_path": entry.absolute_file,
                        "status": tu_record.status,
                        "node_count": tu_record.node_count,
                        "parse_duration_ms": tu_record.parse_duration_ms,
                    },
                )

            if rule_dispatcher and pending_rule_artifacts:
                await self.publish_event(
                    run_id,
                    "rules.started",
                    {"translation_units": len(pending_rule_artifacts)},
                )
                rule_results = rule_dispatcher.execute_for_translation_units(
                    artifacts=pending_rule_artifacts,
                    translation_unit_ids=pending_rule_tu_ids,
                    toolchain_profile=profile,
                    include_graph=include_graph,
                    previous_violations=previous_violations,
                )
                await rule_dispatcher.persist_results(
                    violation_repo,
                    analysis_run_id=run_id,
                    project_id=project_id,
                    results=rule_results,
                )
                await session.commit()
                await self.publish_event(
                    run_id,
                    "rules.completed",
                    {
                        "violations_total": rule_results["statistics"]["violations_total"],
                        "execution_duration_ms": rule_results["statistics"]["execution_duration_ms"],
                    },
                )
                for violation in rule_results["violations"]:
                    await self.publish_event(
                        run_id,
                        "violation.detected",
                        {
                            "rule_id": violation["rule_id"],
                            "file_path": violation["file_path"],
                            "line_start": violation["line_start"],
                            "confidence_score": violation["confidence_score"],
                            "fingerprint": violation["fingerprint"],
                        },
                    )

            for relative_path, node in current_index.items():
                await session.execute(
                    delete(FileIndexEntry).where(
                        FileIndexEntry.project_id == project_id,
                        FileIndexEntry.relative_path == relative_path,
                    )
                )
                session.add(
                    FileIndexEntry(
                        project_id=project_id,
                        relative_path=relative_path,
                        absolute_path=node.absolute_path,
                        content_hash=node.content_hash,
                        include_edges_json=node.include_edges,
                    )
                )

            if run_type == AnalysisRunType.INCREMENTAL:
                session.add(
                    IncrementalManifest(
                        analysis_run_id=run_id,
                        changed_files_json=[],
                        affected_translation_units_json=affected_files,
                        cache_hits=0,
                        cache_misses=parsed_count,
                    )
                )

            run.status = AnalysisStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            run.manifest_json = {
                "compile_commands": str(compile_commands_path),
                "toolchain_profile_id": project.toolchain_profile_id,
                "validation_diagnostics": validation.diagnostics,
                "duplicate_translation_units_removed": validation.duplicate_count,
            }
            await session.commit()
            await clang_client.close()

            await self.publish_event(
                run_id,
                "analysis.completed",
                {
                    "files_total": run.files_total,
                    "files_parsed": run.files_parsed,
                    "files_failed": run.files_failed,
                },
            )
        except Exception as error:
            logger.exception("analysis_run_failed", run_id=str(run_id))
            run.status = AnalysisStatus.FAILED
            run.error_message = str(error)
            run.completed_at = datetime.now(UTC)
            await session.commit()
            await self.publish_event(run_id, "analysis.failed", {"error": str(error)})
