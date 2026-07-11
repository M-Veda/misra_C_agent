import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.domain.enums.violation_status import ViolationStatus
from misra_platform.domain.models.violations import (
    RuleExecutionMetricRecord,
    RuleRunStatisticsRecord,
    ViolationRecord,
)


class ViolationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_violations(
        self,
        *,
        analysis_run_id: uuid.UUID,
        project_id: uuid.UUID,
        translation_unit_id: uuid.UUID | None,
        violations: list[dict],
    ) -> list[ViolationRecord]:
        saved: list[ViolationRecord] = []
        now = datetime.now(UTC)

        for payload in violations:
            fingerprint = payload["fingerprint"]
            existing = await self.session.execute(
                select(ViolationRecord).where(
                    ViolationRecord.project_id == project_id,
                    ViolationRecord.fingerprint == fingerprint,
                )
            )
            record = existing.scalar_one_or_none()
            if record:
                record.analysis_run_id = analysis_run_id
                record.translation_unit_id = translation_unit_id
                record.line_start = payload["line_start"]
                record.line_end = payload["line_end"]
                record.column_start = payload["column_start"]
                record.column_end = payload["column_end"]
                record.confidence_score = payload["confidence_score"]
                record.last_seen_at = now
            else:
                record = ViolationRecord(
                    analysis_run_id=analysis_run_id,
                    translation_unit_id=translation_unit_id,
                    project_id=project_id,
                    rule_id=payload["rule_id"],
                    fingerprint=fingerprint,
                    file_path=payload["file_path"],
                    line_start=payload["line_start"],
                    line_end=payload["line_end"],
                    column_start=payload["column_start"],
                    column_end=payload["column_end"],
                    severity=payload["severity"],
                    confidence_score=payload["confidence_score"],
                    category=payload["category"],
                    offending_expression=payload["offending_expression"],
                    explanation=payload["explanation"],
                    risk_description=payload["risk_description"],
                    source_snippet=payload["source_snippet"],
                    ast_node_reference=payload["ast_node_reference"],
                    macro_expansion_chain_json=payload.get("macro_expansion_chain", []),
                    suggested_fix_json=payload.get("suggested_fix"),
                    confidence_factors_json=payload.get("confidence_factors"),
                    status=ViolationStatus.OPEN,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                self.session.add(record)
            saved.append(record)

        await self.session.flush()
        return saved

    async def list_by_run(self, analysis_run_id: uuid.UUID) -> list[ViolationRecord]:
        result = await self.session.execute(
            select(ViolationRecord)
            .where(ViolationRecord.analysis_run_id == analysis_run_id)
            .order_by(ViolationRecord.file_path.asc(), ViolationRecord.line_start.asc())
        )
        return list(result.scalars().all())

    async def list_by_project(self, project_id: uuid.UUID) -> list[ViolationRecord]:
        result = await self.session.execute(
            select(ViolationRecord)
            .where(ViolationRecord.project_id == project_id)
            .order_by(ViolationRecord.last_seen_at.desc())
        )
        return list(result.scalars().all())

    async def get_previous_fingerprints(self, project_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(ViolationRecord.fingerprint, ViolationRecord.rule_id, ViolationRecord.file_path)
            .where(ViolationRecord.project_id == project_id)
            .distinct()
        )
        return [
            {"fingerprint": row.fingerprint, "rule_id": row.rule_id, "file_path": row.file_path}
            for row in result.all()
        ]

    async def save_execution_metrics(
        self,
        *,
        analysis_run_id: uuid.UUID,
        translation_unit_id: uuid.UUID | None,
        metrics: list[dict],
    ) -> None:
        for metric in metrics:
            self.session.add(
                RuleExecutionMetricRecord(
                    analysis_run_id=analysis_run_id,
                    translation_unit_id=translation_unit_id,
                    rule_id=metric["rule_id"],
                    duration_ms=metric["duration_ms"],
                    violation_count=metric["violation_count"],
                    success=metric["success"],
                    error_message=metric.get("error_message"),
                )
            )

    async def save_run_statistics(self, *, analysis_run_id: uuid.UUID, statistics: dict) -> None:
        self.session.add(
            RuleRunStatisticsRecord(
                analysis_run_id=analysis_run_id,
                rules_executed=statistics.get("rules_executed", 0),
                violations_total=statistics.get("violations_total", 0),
                violations_deduplicated=statistics.get("violations_deduplicated", 0),
                execution_duration_ms=statistics.get("execution_duration_ms", 0.0),
                translation_units_analyzed=statistics.get("translation_units_analyzed", 0),
                metrics_json=statistics.get("metrics_json"),
            )
        )
