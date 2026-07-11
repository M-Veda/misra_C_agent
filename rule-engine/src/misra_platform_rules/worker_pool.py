"""Hierarchical worker pool: Project → Translation Unit → Rule."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from misra_platform_rules.analyzer_efficiency import aggregate_tu_efficiency_stats
from misra_platform_rules.base_rule import IRulePlugin
from misra_platform_rules.engine import ExecutionReport, RuleExecutionEngine
from misra_platform_rules.rule_context import RuleContext


@dataclass(slots=True)
class TranslationUnitJob:
    translation_unit_id: str
    context: RuleContext
    rules: list[IRulePlugin]


@dataclass(slots=True)
class WorkerProgress:
    translation_units_total: int = 0
    translation_units_completed: int = 0
    rules_executed: int = 0
    violations_found: int = 0
    cancelled: bool = False


@dataclass(slots=True)
class ProjectExecutionReport:
    translation_unit_reports: dict[str, ExecutionReport] = field(default_factory=dict)
    progress: WorkerProgress = field(default_factory=WorkerProgress)
    total_duration_ms: float = 0.0
    cache_stats: dict[str, float | int] = field(default_factory=dict)

    def aggregate_cache_stats(self) -> dict[str, float | int]:
        """Sum per-TU AnalysisCache counters into project-level efficiency stats."""
        tu_stats = [
            dict(tu_report.cache_stats)
            for tu_report in self.translation_unit_reports.values()
            if tu_report.cache_stats
        ]
        return aggregate_tu_efficiency_stats(tu_stats)


class WorkerPool:
    def __init__(
        self,
        *,
        tu_workers: int = 2,
        rule_workers: int = 4,
        rule_timeout_seconds: float = 5.0,
    ) -> None:
        self.tu_workers = tu_workers
        self.rule_engine = RuleExecutionEngine(
            max_workers=rule_workers,
            rule_timeout_seconds=rule_timeout_seconds,
        )
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def execute_project(
        self,
        jobs: list[TranslationUnitJob],
        *,
        on_progress: Callable[[WorkerProgress], None] | None = None,
    ) -> ProjectExecutionReport:
        started = time.perf_counter()
        report = ProjectExecutionReport()
        report.progress.translation_units_total = len(jobs)

        with ThreadPoolExecutor(max_workers=self.tu_workers) as executor:
            futures: dict[Future[ExecutionReport], TranslationUnitJob] = {
                executor.submit(self._execute_translation_unit, job): job for job in jobs
            }
            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    report.progress.cancelled = True
                    break
                job = futures[future]
                tu_report = future.result()
                report.translation_unit_reports[job.translation_unit_id] = tu_report
                report.progress.translation_units_completed += 1
                report.progress.rules_executed += len(tu_report.metrics)
                report.progress.violations_found += len(tu_report.violations)
                if on_progress:
                    on_progress(report.progress)

        report.total_duration_ms = (time.perf_counter() - started) * 1000
        report.cache_stats = report.aggregate_cache_stats()
        return report

    def _execute_translation_unit(self, job: TranslationUnitJob) -> ExecutionReport:
        if self._cancel_event.is_set():
            return ExecutionReport()
        return self.rule_engine.execute(job.context, job.rules)


def build_translation_unit_job(
    *,
    artifact: dict[str, Any],
    translation_unit_id: str | uuid.UUID,
    rules: list[IRulePlugin],
    include_graph: dict[str, list[str]] | None = None,
    toolchain_profile: dict[str, Any] | None = None,
    previous_violations: list | None = None,
    cross_tu_linkage: dict[str, Any] | None = None,
) -> TranslationUnitJob:
    context = RuleContext.from_ast_artifact(
        artifact=artifact,
        translation_unit_id=str(translation_unit_id),
        include_graph=include_graph,
        toolchain_profile=toolchain_profile,
        previous_violations=previous_violations,
        cross_tu_linkage=cross_tu_linkage,
    )
    return TranslationUnitJob(
        translation_unit_id=str(translation_unit_id),
        context=context,
        rules=rules,
    )
