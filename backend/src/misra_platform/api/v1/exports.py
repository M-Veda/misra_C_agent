import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.domain.models.analysis import Project
from misra_platform.domain.models.violations import RuleRunStatisticsRecord
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.repositories.violation_repo import ViolationRepository
from misra_platform.services.export_service import ExportService
from misra_platform.services.integration_service import IntegrationService

router = APIRouter(tags=["Enterprise Exports"])


@router.get("/analysis/runs/{run_id}/export/sarif")
async def export_sarif(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    actor_id: str = Query(default="ci-system", min_length=1, max_length=128),
    actor_name: str | None = Query(default=None, max_length=255),
) -> Response:
    violation_repo = ViolationRepository(session)
    enterprise_repo = EnterpriseRepository(session)
    export_service = ExportService(violation_repo)
    integration_service = IntegrationService(enterprise_repo)

    violations = await export_service.load_run_violations(run_id)

    project_id = violations[0].project_id if violations else None
    if project_id is None:
        from misra_platform.domain.models.analysis import AnalysisRun

        run = await session.get(AnalysisRun, run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        project_id = run.project_id

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    sarif = export_service.export_sarif(violations, run_id=run_id, project=project)
    await integration_service.log_export_event(
        run_id=run_id,
        format_name="sarif",
        actor_id=actor_id,
        actor_name=actor_name,
        violation_count=len(violations),
    )
    await session.commit()

    import json

    return Response(
        content=json.dumps(sarif, indent=2),
        media_type="application/sarif+json",
        headers={"Content-Disposition": f'attachment; filename="misra-{run_id}.sarif.json"'},
    )


@router.get("/analysis/runs/{run_id}/export/github-annotations")
async def export_github_annotations(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict:
    violation_repo = ViolationRepository(session)
    export_service = ExportService(violation_repo)
    violations = await export_service.load_run_violations(run_id)
    return {
        "annotations": export_service.export_github_annotations(violations),
        "summary_markdown": export_service.export_github_summary(violations, run_id=run_id),
    }


@router.get("/analysis/runs/{run_id}/export/gitlab-codequality")
async def export_gitlab_codequality(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[dict]:
    violation_repo = ViolationRepository(session)
    export_service = ExportService(violation_repo)
    violations = await export_service.load_run_violations(run_id)
    return export_service.export_gitlab_codequality(violations)
