import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.integrations.enterprise.reviewer_assignment import (
    ReviewerAssignmentError,
    ReviewerAssignmentService,
)
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.repositories.violation_repo import ViolationRepository
from misra_platform.schemas.requests.enterprise import (
    AssignReviewerRequest,
    BulkAssignReviewersRequest,
    JiraSyncRequest,
    PrCommentRequest,
    RoundRobinAssignRequest,
)
from misra_platform.schemas.responses.enterprise import (
    JiraSyncResponse,
    PrCommentResponse,
    ReviewerAssignmentResponse,
)
from misra_platform.services.integration_service import IntegrationService

router = APIRouter(tags=["Enterprise Integrations"])


@router.post(
    "/analysis/runs/{run_id}/integrations/pr-comment",
    response_model=PrCommentResponse,
)
async def build_pr_comment(
    run_id: uuid.UUID,
    request: PrCommentRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PrCommentResponse:
    violation_repo = ViolationRepository(session)
    enterprise_repo = EnterpriseRepository(session)
    integration_service = IntegrationService(enterprise_repo)

    violations = await violation_repo.list_by_run(run_id)
    body = integration_service.build_pr_comment(
        violations, run_id=run_id, platform=request.platform
    )
    inline = integration_service.build_inline_pr_comments(
        violations, max_comments=request.max_inline_comments
    )
    await integration_service.log_export_event(
        run_id=run_id,
        format_name="pr_comment",
        actor_id="ci-system",
        actor_name=None,
        violation_count=len(violations),
    )
    await session.commit()
    return PrCommentResponse(body=body, inline_comments=inline)


@router.post(
    "/analysis/runs/{run_id}/integrations/jira-sync",
    response_model=JiraSyncResponse,
)
async def sync_jira_issues(
    run_id: uuid.UUID,
    request: JiraSyncRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> JiraSyncResponse:
    violation_repo = ViolationRepository(session)
    enterprise_repo = EnterpriseRepository(session)
    integration_service = IntegrationService(enterprise_repo)
    violations = await violation_repo.list_by_run(run_id)

    try:
        results = await integration_service.sync_to_jira(
            violations=violations,
            run_id=run_id,
            base_url=request.base_url,
            email=request.email,
            api_token=request.api_token,
            project_key=request.project_key,
            actor_id=request.actor_id,
            actor_name=request.actor_name,
            max_issues=request.max_issues,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira sync failed: {error}",
        ) from error

    await session.commit()
    return JiraSyncResponse(issues_created=len(results), results=results)


@router.post(
    "/violations/{violation_id}/assign-reviewer",
    response_model=ReviewerAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_reviewer(
    violation_id: uuid.UUID,
    request: AssignReviewerRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ReviewerAssignmentResponse:
    enterprise_repo = EnterpriseRepository(session)
    service = ReviewerAssignmentService(enterprise_repo)
    violation = await enterprise_repo.get_violation(violation_id)
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    try:
        outcome = await service.assign_reviewer(
            violation,
            reviewer_id=request.reviewer_id,
            reviewer_name=request.reviewer_name,
            actor_id=request.actor_id,
            actor_name=request.actor_name,
            team_id=request.team_id,
        )
    except ReviewerAssignmentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    await session.commit()
    return ReviewerAssignmentResponse(
        violation_id=violation.id,
        assigned_reviewer_id=outcome.violation.assigned_reviewer_id or "",
        assigned_reviewer_name=outcome.violation.assigned_reviewer_name or "",
        audit_entry_id=outcome.audit_entry.id,
    )


@router.post(
    "/violations/bulk-assign-reviewer",
    response_model=list[ReviewerAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_assign_reviewer(
    request: BulkAssignReviewersRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[ReviewerAssignmentResponse]:
    enterprise_repo = EnterpriseRepository(session)
    service = ReviewerAssignmentService(enterprise_repo)
    try:
        outcomes = await service.bulk_assign(
            request.violation_ids,
            reviewer_id=request.reviewer_id,
            reviewer_name=request.reviewer_name,
            actor_id=request.actor_id,
            actor_name=request.actor_name,
            team_id=request.team_id,
        )
    except ReviewerAssignmentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    await session.commit()
    return [
        ReviewerAssignmentResponse(
            violation_id=o.violation.id,
            assigned_reviewer_id=o.violation.assigned_reviewer_id or "",
            assigned_reviewer_name=o.violation.assigned_reviewer_name or "",
            audit_entry_id=o.audit_entry.id,
        )
        for o in outcomes
    ]


@router.post(
    "/integrations/round-robin-assign",
    response_model=list[ReviewerAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def round_robin_assign(
    request: RoundRobinAssignRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[ReviewerAssignmentResponse]:
    violation_repo = ViolationRepository(session)
    enterprise_repo = EnterpriseRepository(session)
    service = ReviewerAssignmentService(enterprise_repo)
    violations = await violation_repo.list_by_run(request.run_id)
    open_violations = [v for v in violations if v.status == "open"]

    try:
        outcomes = await service.auto_assign_round_robin(
            open_violations,
            request.team_id,
            actor_id=request.actor_id,
            actor_name=request.actor_name,
        )
    except ReviewerAssignmentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    await session.commit()
    return [
        ReviewerAssignmentResponse(
            violation_id=o.violation.id,
            assigned_reviewer_id=o.violation.assigned_reviewer_id or "",
            assigned_reviewer_name=o.violation.assigned_reviewer_name or "",
            audit_entry_id=o.audit_entry.id,
        )
        for o in outcomes
    ]
