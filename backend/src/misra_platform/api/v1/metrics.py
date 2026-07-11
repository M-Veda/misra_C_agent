from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.core.dependencies import get_database_session
from misra_platform.schemas.responses.metrics import (
    ConfidenceDistributionResponse,
    ReviewAcceptanceRateResponse,
    RuleTimingSummaryResponse,
)
from misra_platform.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/confidence-distribution", response_model=ConfidenceDistributionResponse)
async def get_confidence_distribution(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    project_id: Annotated[str | None, Query()] = None,
    rule_id: Annotated[str | None, Query()] = None,
) -> ConfidenceDistributionResponse:
    service = MetricsService(session)
    data = await service.confidence_distribution(project_id=project_id, rule_id=rule_id)
    return ConfidenceDistributionResponse.model_validate(data)


@router.get("/review-acceptance-rate", response_model=ReviewAcceptanceRateResponse)
async def get_review_acceptance_rate(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    rule_id: Annotated[str | None, Query()] = None,
) -> ReviewAcceptanceRateResponse:
    service = MetricsService(session)
    data = await service.review_acceptance_rate(rule_id=rule_id)
    return ReviewAcceptanceRateResponse.model_validate(data)


@router.get("/rule-timing-summary", response_model=RuleTimingSummaryResponse)
async def get_rule_timing_summary(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> RuleTimingSummaryResponse:
    service = MetricsService(session)
    timing = await service.rule_timing_summary()
    return RuleTimingSummaryResponse(timing_by_rule=timing)
