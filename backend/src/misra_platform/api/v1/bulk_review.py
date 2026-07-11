from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.repositories.review_repo import ReviewRepository
from misra_platform.schemas.responses.review import (
    BulkAssignReviewerRequest,
    BulkAssignReviewerResponse,
    BulkExportPatchesRequest,
    BulkExportPatchesResponse,
    BulkSkipRequest,
    BulkSkipResponse,
)
from misra_platform.services.bulk_review_service import BulkReviewService
from misra_platform.services.review_service import ReviewService

router = APIRouter(prefix="/violations/bulk", tags=["Bulk Review"])


@router.post("/skip", response_model=BulkSkipResponse)
async def bulk_skip_violations(
    request: BulkSkipRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BulkSkipResponse:
    repo = ReviewRepository(session)
    bulk_service = BulkReviewService(repo, ReviewService(repo))

    result = await bulk_service.bulk_skip(
        violation_ids=request.violation_ids,
        reviewer_id=request.reviewer_id,
        reviewer_name=request.reviewer_name,
        notes=request.notes,
    )

    await session.commit()
    return BulkSkipResponse(
        skipped_violation_ids=result.skipped_violation_ids,
        not_found_violation_ids=result.not_found_violation_ids,
    )


@router.post("/assign-reviewer", response_model=BulkAssignReviewerResponse)
async def bulk_assign_reviewer(
    request: BulkAssignReviewerRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BulkAssignReviewerResponse:
    repo = ReviewRepository(session)
    bulk_service = BulkReviewService(repo, ReviewService(repo))

    result = await bulk_service.bulk_assign_reviewer(
        violation_ids=request.violation_ids,
        reviewer_id=request.reviewer_id,
        reviewer_name=request.reviewer_name,
        assigned_by=request.assigned_by,
    )
    await session.commit()
    return BulkAssignReviewerResponse(
        assigned_violation_ids=result.assigned_violation_ids,
        not_found_violation_ids=result.not_found_violation_ids,
    )


@router.post("/export-patches", response_model=BulkExportPatchesResponse)
async def bulk_export_patches(
    request: BulkExportPatchesRequest,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BulkExportPatchesResponse:
    repo = ReviewRepository(session)
    bulk_service = BulkReviewService(repo, ReviewService(repo))

    result = await bulk_service.bulk_export_approved_patches(
        violation_ids=request.violation_ids,
        exported_by=request.exported_by,
    )
    await session.commit()
    return BulkExportPatchesResponse(
        combined_patch=result.combined_patch,
        exported_patch_ids=result.exported_patch_ids,
        skipped_violation_ids=result.skipped_violation_ids,
    )
