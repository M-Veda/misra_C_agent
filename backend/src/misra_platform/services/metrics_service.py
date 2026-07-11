"""Phase 3 metrics: confidence distribution and review acceptance rate.

Rule timing and false-positive-candidate counts are computed per analysis
run in `RuleDispatcher` (see `_confidence_distribution` there) and persisted
into `RuleRunStatisticsRecord.metrics_json`. The metrics here are
project/rule-wide and span every review action ever taken, so they are
computed on demand rather than snapshotted at analysis time.
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.domain.models.review import ViolationReviewRecord
from misra_platform.domain.models.violations import ViolationRecord

_ACCEPTING_ACTIONS = {"accept", "edit"}
_DECISIVE_ACTIONS = {"accept", "edit", "reject", "false_positive", "suppress"}
_CONFIDENCE_BUCKETS = [
    ("0.0-0.2", 0.0, 0.2),
    ("0.2-0.4", 0.2, 0.4),
    ("0.4-0.6", 0.4, 0.6),
    ("0.6-0.8", 0.6, 0.8),
    ("0.8-1.0", 0.8, 1.0001),
]


class MetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def confidence_distribution(
        self, *, project_id: str | None = None, rule_id: str | None = None
    ) -> dict[str, Any]:
        query = select(ViolationRecord.confidence_score, ViolationRecord.rule_id)
        if project_id:
            query = query.where(ViolationRecord.project_id == project_id)
        if rule_id:
            query = query.where(ViolationRecord.rule_id == rule_id)

        result = await self.session.execute(query)
        rows = result.all()

        overall = {label: 0 for label, _, _ in _CONFIDENCE_BUCKETS}
        by_rule: dict[str, dict[str, int]] = defaultdict(
            lambda: {label: 0 for label, _, _ in _CONFIDENCE_BUCKETS}
        )
        for score, row_rule_id in rows:
            for label, low, high in _CONFIDENCE_BUCKETS:
                if low <= score < high:
                    overall[label] += 1
                    by_rule[row_rule_id][label] += 1
                    break

        return {
            "total_violations": len(rows),
            "overall": overall,
            "by_rule": dict(by_rule),
        }

    async def review_acceptance_rate(
        self, *, rule_id: str | None = None
    ) -> dict[str, Any]:
        query = select(
            ViolationReviewRecord.action, ViolationRecord.rule_id
        ).join(ViolationRecord, ViolationReviewRecord.violation_id == ViolationRecord.id)
        if rule_id:
            query = query.where(ViolationRecord.rule_id == rule_id)

        result = await self.session.execute(query)
        rows = result.all()

        action_counts: dict[str, int] = defaultdict(int)
        by_rule_action_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for action, row_rule_id in rows:
            action_counts[action] += 1
            by_rule_action_counts[row_rule_id][action] += 1

        decisive_total = sum(count for action, count in action_counts.items() if action in _DECISIVE_ACTIONS)
        accepted_total = sum(count for action, count in action_counts.items() if action in _ACCEPTING_ACTIONS)

        by_rule: dict[str, dict[str, Any]] = {}
        for rid, counts in by_rule_action_counts.items():
            decisive = sum(c for a, c in counts.items() if a in _DECISIVE_ACTIONS)
            accepted = sum(c for a, c in counts.items() if a in _ACCEPTING_ACTIONS)
            by_rule[rid] = {
                "action_counts": dict(counts),
                "acceptance_rate": (accepted / decisive) if decisive else None,
            }

        return {
            "action_counts": dict(action_counts),
            "overall_acceptance_rate": (accepted_total / decisive_total) if decisive_total else None,
            "decisive_review_count": decisive_total,
            "by_rule": by_rule,
        }

    async def rule_timing_summary(self) -> dict[str, Any]:
        """Aggregate `RuleExecutionMetricRecord` timing across every run seen so far."""
        from misra_platform.domain.models.violations import RuleExecutionMetricRecord

        result = await self.session.execute(
            select(
                RuleExecutionMetricRecord.rule_id,
                func.avg(RuleExecutionMetricRecord.duration_ms),
                func.max(RuleExecutionMetricRecord.duration_ms),
                func.count(RuleExecutionMetricRecord.id),
            ).group_by(RuleExecutionMetricRecord.rule_id)
        )
        return {
            rule_id: {"avg_ms": avg_ms, "max_ms": max_ms, "invocations": invocations}
            for rule_id, avg_ms, max_ms, invocations in result.all()
        }
