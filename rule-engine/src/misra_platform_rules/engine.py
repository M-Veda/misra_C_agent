import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from misra_platform_rules.base_rule import IRulePlugin
from misra_platform_rules.confidence import score_confidence
from misra_platform_rules.execution_planner import resolve_execution_groups
from misra_platform_rules.fingerprint import generate_fingerprint
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleResult


@dataclass(slots=True)
class RuleExecutionMetrics:
    rule_id: str
    duration_ms: float
    violation_count: int
    success: bool
    error_message: str | None = None


@dataclass(slots=True)
class ExecutionReport:
    violations: list[RuleResult] = field(default_factory=list)
    fingerprints: list[str] = field(default_factory=list)
    metrics: list[RuleExecutionMetrics] = field(default_factory=list)
    deduplicated_count: int = 0
    cache_stats: dict[str, float | int] | None = None


class RuleExecutionEngine:
    def __init__(
        self,
        *,
        max_workers: int = 4,
        rule_timeout_seconds: float = 5.0,
        max_retries: int = 1,
    ) -> None:
        self.max_workers = max_workers
        self.rule_timeout_seconds = rule_timeout_seconds
        self.max_retries = max_retries

    def execute(
        self,
        context: RuleContext,
        rules: list[IRulePlugin],
        *,
        grouped: bool = False,
    ) -> ExecutionReport:
        """Run `rules` against `context`.

        By default every rule runs concurrently in a single wave (`grouped`
        `False`) — safe today because no shipped rule reads another rule's
        output. When `grouped` is `True`, rules are staged via
        `resolve_execution_groups` (category execution order + declared
        `rule_dependencies`) so a rule's dependencies are guaranteed to have
        already run in an earlier wave.
        """
        report = ExecutionReport()

        waves = resolve_execution_groups(rules) if grouped else [rules]
        for wave in waves:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._execute_rule_safe, rule, context): rule for rule in wave
                }
                for future in as_completed(futures):
                    metrics, violations = future.result()
                    report.metrics.append(metrics)
                    report.violations.extend(violations)

        deduplicated, removed = self._deduplicate(report.violations)
        report.violations = deduplicated
        report.deduplicated_count = removed
        report.fingerprints = [generate_fingerprint(violation) for violation in report.violations]
        if context.analysis_cache is not None:
            report.cache_stats = context.analysis_cache.stats()
        return report

    def _execute_rule_safe(
        self,
        rule: IRulePlugin,
        context: RuleContext,
    ) -> tuple[RuleExecutionMetrics, list[RuleResult]]:
        started = time.perf_counter()
        attempts = 0
        last_error: str | None = None

        while attempts <= self.max_retries:
            attempts += 1
            try:
                violations = rule.detect(context)
                for violation in violations:
                    violation.confidence_score = score_confidence(violation)
                duration_ms = (time.perf_counter() - started) * 1000
                return RuleExecutionMetrics(
                    rule_id=rule.metadata.rule_id,
                    duration_ms=duration_ms,
                    violation_count=len(violations),
                    success=True,
                ), violations
            except Exception:
                last_error = traceback.format_exc(limit=3)
                if attempts > self.max_retries:
                    break

        duration_ms = (time.perf_counter() - started) * 1000
        return RuleExecutionMetrics(
            rule_id=rule.metadata.rule_id,
            duration_ms=duration_ms,
            violation_count=0,
            success=False,
            error_message=last_error or "unknown rule failure",
        ), []

    def _deduplicate(self, violations: list[RuleResult]) -> tuple[list[RuleResult], int]:
        seen: set[str] = set()
        unique: list[RuleResult] = []
        removed = 0
        for violation in violations:
            fingerprint = generate_fingerprint(violation)
            if fingerprint in seen:
                removed += 1
                continue
            seen.add(fingerprint)
            unique.append(violation)
        return unique, removed
