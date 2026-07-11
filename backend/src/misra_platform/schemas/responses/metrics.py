from typing import Any

from pydantic import BaseModel


class ConfidenceDistributionResponse(BaseModel):
    total_violations: int
    overall: dict[str, int]
    by_rule: dict[str, dict[str, int]]


class ReviewAcceptanceRateResponse(BaseModel):
    action_counts: dict[str, int]
    overall_acceptance_rate: float | None
    decisive_review_count: int
    by_rule: dict[str, dict[str, Any]]


class RuleTimingSummaryResponse(BaseModel):
    timing_by_rule: dict[str, dict[str, float]]
