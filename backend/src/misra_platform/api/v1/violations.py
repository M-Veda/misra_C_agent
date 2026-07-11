import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.domain.models.violations import RuleRunStatisticsRecord, ViolationRecord
from misra_platform.repositories.violation_repo import ViolationRepository
from misra_platform.schemas.responses.rules import RuleRunStatisticsResponse, ViolationResponse

router = APIRouter(tags=["Violations"])


@router.get("/violations/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ViolationRecord:
    violation = await session.get(ViolationRecord, violation_id)
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")
    return violation


@router.get("/analysis/runs/{run_id}/violations", response_model=list[ViolationResponse])
async def list_run_violations(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[ViolationRecord]:
    repo = ViolationRepository(session)
    return await repo.list_by_run(run_id)


@router.get("/projects/{project_id}/violations", response_model=list[ViolationResponse])
async def list_project_violations(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[ViolationRecord]:
    repo = ViolationRepository(session)
    return await repo.list_by_project(project_id)


@router.get(
    "/analysis/runs/{run_id}/rule-statistics",
    response_model=RuleRunStatisticsResponse,
)
async def get_rule_run_statistics(
    run_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RuleRunStatisticsRecord:
    result = await session.execute(
        select(RuleRunStatisticsRecord).where(RuleRunStatisticsRecord.analysis_run_id == run_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule execution statistics not found for this run",
        )
    return record
