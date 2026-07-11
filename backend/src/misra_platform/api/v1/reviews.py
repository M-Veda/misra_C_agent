import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.domain.models.analysis import Project
from misra_platform.repositories.review_repo import ReviewRepository
from misra_platform.schemas.responses.review import (
    AuditEntryResponse,
    ImpactEstimateResponse,
    PatchResponse,
    ReviewActionRequest,
    SourceWindowResponse,
    SubmitReviewResponse,
    ViolationReviewResponse,
)
from misra_platform.services.review_service import (
    ReviewService,
    ReviewValidationError,
    estimate_impact,
)
from misra_platform.services.source_file_service import SourceFileService

router = APIRouter(tags=["Review"])


async def _get_project_root(session: AsyncSession, project_id: uuid.UUID) -> str:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project.root_path


@router.post(
    "/violations/{violation_id}/reviews",
    response_model=SubmitReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    violation_id: uuid.UUID,
    request: ReviewActionRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SubmitReviewResponse:
    repo = ReviewRepository(session)
    violation = await repo.get_violation(violation_id)
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    project_root = await _get_project_root(session, violation.project_id)
    service = ReviewService(repo)

    try:
        outcome = await service.submit_review(
            violation=violation,
            project_root=project_root,
            action=request.action,
            reviewer_id=request.reviewer_id,
            reviewer_name=request.reviewer_name,
            justification=request.justification,
            notes=request.notes,
            edited_fix=request.edited_fix.model_dump() if request.edited_fix else None,
        )
    except ReviewValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    await session.commit()

    return SubmitReviewResponse(
        review=ViolationReviewResponse.model_validate(outcome.review),
        audit_entry=AuditEntryResponse.model_validate(outcome.audit_entry),
        patch=PatchResponse.model_validate(outcome.patch) if outcome.patch else None,
        violation_status=violation.status,
    )


@router.get(
    "/violations/{violation_id}/reviews",
    response_model=list[ViolationReviewResponse],
)
async def list_violation_reviews(
    violation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[ViolationReviewResponse]:
    repo = ReviewRepository(session)
    reviews = await repo.list_reviews(violation_id)
    return [ViolationReviewResponse.model_validate(review) for review in reviews]


@router.get(
    "/violations/{violation_id}/patches",
    response_model=list[PatchResponse],
)
async def list_violation_patches(
    violation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> list[PatchResponse]:
    repo = ReviewRepository(session)
    patches = await repo.list_patches(violation_id)
    return [PatchResponse.model_validate(patch) for patch in patches]


@router.get("/violations/{violation_id}/source", response_model=SourceWindowResponse)
async def get_violation_source(
    violation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    context: int = Query(default=25, ge=0, le=200),
) -> SourceWindowResponse:
    repo = ReviewRepository(session)
    violation = await repo.get_violation(violation_id)
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    project_root = await _get_project_root(session, violation.project_id)
    source_files = SourceFileService()
    window = source_files.read_window(
        project_root,
        violation.file_path,
        line_start=violation.line_start,
        line_end=violation.line_end,
        context=context,
    )
    return SourceWindowResponse(
        file_path=window.file_path,
        start_line=window.start_line,
        end_line=window.end_line,
        lines=window.lines,
        highlight_start=window.highlight_start,
        highlight_end=window.highlight_end,
        available=window.available,
    )


@router.get("/violations/{violation_id}/impact", response_model=ImpactEstimateResponse)
async def get_violation_impact(
    violation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ImpactEstimateResponse:
    repo = ReviewRepository(session)
    violation = await repo.get_violation(violation_id)
    if not violation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")
    return ImpactEstimateResponse.model_validate(estimate_impact(violation))


@router.get(
    "/violations/{violation_id}/patches/{patch_id}/export",
    response_class=Response,
)
async def export_patch(
    violation_id: uuid.UUID,
    patch_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    exported_by: str = Query(min_length=1, max_length=128),
    format: str = Query(default="git", pattern="^(git|unified)$"),
) -> Response:
    repo = ReviewRepository(session)
    patch = await repo.get_patch(patch_id)
    if not patch or patch.violation_id != violation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patch not found")

    await repo.mark_patch_exported(patch, exported_by)
    await session.commit()

    body = patch.git_patch if format == "git" else patch.unified_diff
    extension = "patch" if format == "git" else "diff"
    filename = f"{violation_id}.{extension}"
    return Response(
        content=body,
        media_type="text/x-patch",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-entries", response_model=list[AuditEntryResponse])
async def search_audit_entries(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    q: str | None = Query(default=None, description="Search justification and notes text"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEntryResponse]:
    repo = ReviewRepository(session)
    entries = await repo.search_audit_entries(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        search_text=q,
        limit=limit,
        offset=offset,
    )
    return [AuditEntryResponse.model_validate(entry) for entry in entries]
