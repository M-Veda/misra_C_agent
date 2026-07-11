"""Compliance trends and historical analytics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from misra_platform.domain.models.enterprise import ComplianceSnapshotRecord
from misra_platform.domain.models.violations import RuleRunStatisticsRecord, ViolationRecord
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.repositories.violation_repo import ViolationRepository


@dataclass(slots=True)
class TeamDashboardSummary:
    project_id: uuid.UUID
    team_id: uuid.UUID | None
    violations_open: int
    violations_resolved: int
    violations_total: int
    compliance_score: float
    rules_executed: int
    assigned_pending: int
    trend_direction: str


class ComplianceAnalyticsService:
    def __init__(
        self,
        enterprise_repo: EnterpriseRepository,
        violation_repo: ViolationRepository,
    ) -> None:
        self.enterprise_repo = enterprise_repo
        self.violation_repo = violation_repo

    def compute_compliance_score(
        self,
        *,
        violations_total: int,
        violations_resolved: int,
        rules_executed: int,
    ) -> float:
        if rules_executed == 0:
            return 100.0
        if violations_total == 0:
            return 100.0
        resolution_rate = violations_resolved / violations_total
        density_penalty = min(violations_total / max(rules_executed, 1), 1.0)
        score = round((resolution_rate * 0.6 + (1 - density_penalty) * 0.4) * 100, 2)
        return max(0.0, min(100.0, score))

    async def capture_snapshot(
        self,
        *,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        violations: list[ViolationRecord],
        statistics: RuleRunStatisticsRecord | None,
        team_id: uuid.UUID | None = None,
    ) -> ComplianceSnapshotRecord:
        open_count = sum(1 for v in violations if v.status == "open")
        resolved_count = sum(1 for v in violations if v.status in ("accepted", "fixed", "waived"))
        rules_executed = statistics.rules_executed if statistics else 0
        score = self.compute_compliance_score(
            violations_total=len(violations),
            violations_resolved=resolved_count,
            rules_executed=rules_executed,
        )
        by_severity: dict[str, int] = {}
        by_rule: dict[str, int] = {}
        for v in violations:
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
            by_rule[v.rule_id] = by_rule.get(v.rule_id, 0) + 1

        snapshot = ComplianceSnapshotRecord(
            project_id=project_id,
            analysis_run_id=run_id,
            team_id=team_id,
            violations_total=len(violations),
            violations_open=open_count,
            violations_resolved=resolved_count,
            rules_executed=rules_executed,
            compliance_score=score,
            metrics_json={"by_severity": by_severity, "by_rule": by_rule},
        )
        return await self.enterprise_repo.save_snapshot(snapshot)

    async def team_dashboard(
        self,
        *,
        project_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
    ) -> TeamDashboardSummary:
        violations = await self.violation_repo.list_by_project(project_id)
        open_count = sum(1 for v in violations if v.status == "open")
        resolved_count = sum(1 for v in violations if v.status in ("accepted", "fixed", "waived"))
        assigned_pending = sum(
            1 for v in violations if v.status == "open" and v.assigned_reviewer_id
        )

        snapshots = await self.enterprise_repo.list_snapshots(
            project_id=project_id, team_id=team_id, limit=2
        )
        trend = "stable"
        if len(snapshots) >= 2:
            delta = snapshots[0].compliance_score - snapshots[1].compliance_score
            if delta > 1:
                trend = "improving"
            elif delta < -1:
                trend = "declining"

        latest_score = snapshots[0].compliance_score if snapshots else 100.0
        rules_executed = snapshots[0].rules_executed if snapshots else 0

        return TeamDashboardSummary(
            project_id=project_id,
            team_id=team_id,
            violations_open=open_count,
            violations_resolved=resolved_count,
            violations_total=len(violations),
            compliance_score=latest_score,
            rules_executed=rules_executed,
            assigned_pending=assigned_pending,
            trend_direction=trend,
        )

    async def compliance_trends(
        self,
        *,
        project_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
        limit: int = 30,
    ) -> list[dict]:
        snapshots = await self.enterprise_repo.list_snapshots(
            project_id=project_id, team_id=team_id, limit=limit
        )
        return [
            {
                "captured_at": snapshot.captured_at.isoformat(),
                "analysis_run_id": str(snapshot.analysis_run_id),
                "violations_total": snapshot.violations_total,
                "violations_open": snapshot.violations_open,
                "violations_resolved": snapshot.violations_resolved,
                "compliance_score": snapshot.compliance_score,
                "rules_executed": snapshot.rules_executed,
                "metrics": snapshot.metrics_json,
            }
            for snapshot in reversed(snapshots)
        ]
