from fastapi import APIRouter, HTTPException, status

from misra_platform.schemas.responses.rules import (
    CoverageMatrixResponse,
    ImplementationRoadmapResponse,
    RuleCoverageResponse,
    RuleDetailResponse,
    RuleExamplesResponse,
    RuleMetadataResponse,
)
from misra_platform.services.rule_catalog_service import get_rule_catalog_service

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get("/catalog", response_model=list[RuleMetadataResponse])
async def list_rule_catalog() -> list[RuleMetadataResponse]:
    service = get_rule_catalog_service()
    return [RuleMetadataResponse.model_validate(item) for item in service.list_catalog()]


@router.get("/catalog/coverage", response_model=RuleCoverageResponse)
async def get_rule_coverage() -> RuleCoverageResponse:
    service = get_rule_catalog_service()
    return RuleCoverageResponse.model_validate(service.coverage_summary())


@router.get("/catalog/coverage-matrix", response_model=CoverageMatrixResponse)
async def get_rule_coverage_matrix() -> CoverageMatrixResponse:
    """Phase 3 deliverable: full MISRA C:2012 taxonomy/coverage matrix."""
    service = get_rule_catalog_service()
    return CoverageMatrixResponse.model_validate(service.full_coverage_matrix())


@router.get("/catalog/roadmap", response_model=ImplementationRoadmapResponse)
async def get_implementation_roadmap() -> ImplementationRoadmapResponse:
    """Phase 4 deliverable: per-rule capability requirements (AST/type/CFG/
    dataflow/linkage/alias) plus an automatically-generated implementation
    readiness tier for every not-yet-implemented rule."""
    service = get_rule_catalog_service()
    return ImplementationRoadmapResponse.model_validate(service.implementation_roadmap())


@router.get("/catalog/{rule_id}", response_model=RuleDetailResponse)
async def get_rule_detail(rule_id: str) -> RuleDetailResponse:
    service = get_rule_catalog_service()
    try:
        metadata = service.get_rule(rule_id)
        examples = service.get_examples(rule_id)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return RuleDetailResponse(
        **RuleMetadataResponse.model_validate(metadata).model_dump(),
        examples=RuleExamplesResponse.model_validate(examples),
    )
