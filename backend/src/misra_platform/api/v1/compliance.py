import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.domain.models.analysis import AnalysisRun
from misra_platform.domain.models.violations import RuleRunStatisticsRecord
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.repositories.violation_repo import ViolationRepository
from misra_platform.schemas.requests.enterprise import CaptureSnapshotRequest
from misra_platform.schemas.responses.enterprise import (
    ComplianceSnapshotResponse,
    ComplianceTrendPoint,
    TeamDashboardResponse,
)
from misra_platform.services.compliance_analytics_service import ComplianceAnalyticsService

router = APIRouter(tags=["Compliance Analytics"])


@router.get("/projects/{project_id}/dashboard", response_model=TeamDashboardResponse)
async def get_team_dashboard(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    team_id: uuid.UUID | None = None,
) -> TeamDashboardResponse:
    enterprise_repo = EnterpriseRepository(session)
    violation_repo = ViolationRepository(session)
    service = ComplianceAnalyticsService(enterprise_repo, violation_repo)
    summary = await service.team_dashboard(project_id=project_id, team_id=team_id)
    return TeamDashboardResponse(
        project_id=summary.project_id,
        team_id=summary.team_id,
        violations_open=summary.violations_open,
        violations_resolved=summary.violations_resolved,
        violations_total=summary.violations_total,
        compliance_score=summary.compliance_score,
        rules_executed=summary.rules_executed,
        assigned_pending=summary.assigned_pending,
        trend_direction=summary.trend_direction,
    )


@router.get(
    "/projects/{project_id}/compliance-trends",
    response_model=list[ComplianceTrendPoint],
)
async def get_compliance_trends(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    team_id: uuid.UUID | None = None,
    limit: int = Query(default=30, ge=1, le=365),
) -> list[ComplianceTrendPoint]:
    enterprise_repo = EnterpriseRepository(session)
    violation_repo = ViolationRepository(session)
    service = ComplianceAnalyticsService(enterprise_repo, violation_repo)
    trends = await service.compliance_trends(
        project_id=project_id, team_id=team_id, limit=limit
    )
    return [ComplianceTrendPoint.model_validate(point) for point in trends]


@router.post(
    "/analysis/runs/{run_id}/compliance-snapshot",
    response_model=ComplianceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def capture_compliance_snapshot(
    run_id: uuid.UUID,
    request: CaptureSnapshotRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ComplianceSnapshotResponse:
    violation_repo = ViolationRepository(session)
    enterprise_repo = EnterpriseRepository(session)
    service = ComplianceAnalyticsService(enterprise_repo, violation_repo)

    violations = await violation_repo.list_by_run(run_id)
    if violations:
        project_id = violations[0].project_id
    else:
        run = await session.get(AnalysisRun, run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        project_id = run.project_id

    stats_result = await session.execute(
        select(RuleRunStatisticsRecord).where(RuleRunStatisticsRecord.analysis_run_id == run_id)
    )
    statistics = stats_result.scalar_one_or_none()
    snapshot = await service.capture_snapshot(
        project_id=project_id,
        run_id=run_id,
        violations=violations,
        statistics=statistics,
        team_id=request.team_id,
    )
    await session.commit()
    return ComplianceSnapshotResponse.model_validate(snapshot)
