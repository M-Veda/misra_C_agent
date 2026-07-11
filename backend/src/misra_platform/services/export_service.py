"""Export orchestration for SARIF and CI annotation formats."""

from __future__ import annotations

import uuid

from misra_platform.domain.models.analysis import Project
from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.integrations.enterprise.github_annotations import GitHubAnnotationExporter
from misra_platform.integrations.enterprise.gitlab_annotations import GitLabCodeQualityExporter
from misra_platform.integrations.enterprise.sarif_exporter import SarifExporter
from misra_platform.repositories.violation_repo import ViolationRepository


def violation_to_dict(violation: ViolationRecord) -> dict:
    return {
        "rule_id": violation.rule_id,
        "fingerprint": violation.fingerprint,
        "file_path": violation.file_path,
        "line_start": violation.line_start,
        "line_end": violation.line_end,
        "column_start": violation.column_start,
        "column_end": violation.column_end,
        "severity": violation.severity,
        "confidence_score": violation.confidence_score,
        "category": violation.category,
        "explanation": violation.explanation,
        "risk_description": violation.risk_description,
        "status": violation.status,
        "assigned_reviewer_id": violation.assigned_reviewer_id,
    }


class ExportService:
    def __init__(self, violation_repo: ViolationRepository) -> None:
        self.violation_repo = violation_repo
        self.sarif = SarifExporter()
        self.github = GitHubAnnotationExporter()
        self.gitlab = GitLabCodeQualityExporter()

    async def load_run_violations(self, run_id: uuid.UUID) -> list[ViolationRecord]:
        return await self.violation_repo.list_by_run(run_id)

    def export_sarif(
        self,
        violations: list[ViolationRecord],
        *,
        run_id: uuid.UUID,
        project: Project,
    ) -> dict:
        payload = [violation_to_dict(v) for v in violations]
        return self.sarif.export(payload, run_id=str(run_id), project_name=project.name)

    def export_github_annotations(self, violations: list[ViolationRecord]) -> list[str]:
        return self.github.export([violation_to_dict(v) for v in violations])

    def export_github_summary(self, violations: list[ViolationRecord], *, run_id: uuid.UUID) -> str:
        return self.github.export_summary_markdown(
            [violation_to_dict(v) for v in violations], run_id=str(run_id)
        )

    def export_gitlab_codequality(self, violations: list[ViolationRecord]) -> list[dict]:
        return self.gitlab.export([violation_to_dict(v) for v in violations])
