"""Rule-engine performance benchmark harness (Phase 3).

Measures actual throughput of the full 36-rule set against a synthetic
project, then linearly extrapolates to the 100K LOC / 500K LOC / incremental
performance targets. Can be run standalone (``python benchmark_rule_engine.py``)
or invoked from `test_performance.py` as part of the test suite.

Methodology and caveats are documented in `docs/PHASE_3.md`.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _THIS_DIR.parent
for _path in (_THIS_DIR, _TESTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from misra_platform_rules.analyzer_efficiency import (  # noqa: E402
    build_reuse_report,
    build_top_analyzer_costs,
    project_cache_report_from_execution,
    write_preflight_reports,
)
from misra_platform_rules.analyzers import LinkageIndex  # noqa: E402
from misra_platform_rules.ast_graph import AstGraph  # noqa: E402
from misra_platform_rules.registry import create_default_registry  # noqa: E402
from misra_platform_rules.worker_pool import WorkerPool, build_translation_unit_job  # noqa: E402
from synthetic_project import build_project  # noqa: E402

TARGET_100K_LOC_SECONDS = 10 * 60
TARGET_500K_LOC_SECONDS = 30 * 60
TARGET_INCREMENTAL_FRACTION = 0.25


@dataclass(slots=True)
class BenchmarkResult:
    label: str
    translation_units: int
    loc: int
    functions: int
    duration_ms: float
    violations_found: int
    rule_count: int = 0
    throughput_loc_per_sec: float = 0.0
    throughput_functions_per_sec: float = 0.0
    rule_timings_top_slowest: list[dict[str, Any]] = field(default_factory=list)
    cache_stats: dict[str, Any] = field(default_factory=dict)


def _cross_tu_linkage(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    return LinkageIndex.build(
        [
            (str(index), artifact.get("file_path", ""), AstGraph(artifact.get("nodes", [])))
            for index, artifact in enumerate(artifacts)
        ]
    )


def aggregate_rule_timings(report: Any, top_n: int = 10) -> list[dict[str, Any]]:
    """Aggregates per-rule `RuleExecutionMetrics.duration_ms` across every
    translation unit in a `ProjectExecutionReport`, returning the `top_n`
    slowest rules by total wall-clock time spent (sum across all TUs where
    that rule ran), so a single slow rule shows up even if the project has
    many small/fast translation units diluting a plain average."""
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for tu_report in report.translation_unit_reports.values():
        for metric in tu_report.metrics:
            totals[metric.rule_id] = totals.get(metric.rule_id, 0.0) + metric.duration_ms
            counts[metric.rule_id] = counts.get(metric.rule_id, 0) + 1

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [
        {
            "rule_id": rule_id,
            "total_duration_ms": round(total_ms, 4),
            "invocations": counts[rule_id],
            "avg_duration_ms": round(total_ms / counts[rule_id], 5) if counts[rule_id] else 0.0,
        }
        for rule_id, total_ms in ranked
    ]


def run_measured_project(
    *, translation_units: int, functions_per_tu: int = 40, tu_workers: int = 8, rule_workers: int = 4
) -> tuple[BenchmarkResult, Any]:
    project = build_project(translation_units=translation_units, functions_per_tu=functions_per_tu)
    registry = create_default_registry()
    rules = registry.select_rules(None)

    linkage = _cross_tu_linkage(project.artifacts)
    jobs = [
        build_translation_unit_job(
            artifact=artifact,
            translation_unit_id=str(index),
            rules=rules,
            cross_tu_linkage=linkage,
        )
        for index, artifact in enumerate(project.artifacts)
    ]

    pool = WorkerPool(tu_workers=tu_workers, rule_workers=rule_workers)
    started = time.perf_counter()
    report = pool.execute_project(jobs)
    elapsed_ms = (time.perf_counter() - started) * 1000
    elapsed_seconds = elapsed_ms / 1000.0

    return BenchmarkResult(
        label=f"{project.loc_total} LOC synthetic ({translation_units} TUs)",
        translation_units=translation_units,
        loc=project.loc_total,
        functions=project.functions_total,
        duration_ms=elapsed_ms,
        violations_found=report.progress.violations_found,
        rule_count=len(rules),
        throughput_loc_per_sec=round(project.loc_total / elapsed_seconds, 2) if elapsed_seconds else 0.0,
        throughput_functions_per_sec=(
            round(project.functions_total / elapsed_seconds, 2) if elapsed_seconds else 0.0
        ),
        rule_timings_top_slowest=aggregate_rule_timings(report),
        cache_stats=dict(report.cache_stats),
    ), report


def extrapolate(baseline: BenchmarkResult, target_loc: int) -> float:
    """Linear extrapolation of measured ms/LOC to a target project size."""
    ms_per_loc = baseline.duration_ms / baseline.loc
    return (ms_per_loc * target_loc) / 1000.0


def run_incremental(
    baseline_tus: int, changed_tus: int, functions_per_tu: int = 40
) -> tuple[BenchmarkResult, Any]:
    """Simulate an incremental run: only `changed_tus` translation units are
    re-analyzed (as a real incremental analyzer would do after detecting
    which files changed since the last run)."""
    return run_measured_project(translation_units=changed_tus, functions_per_tu=functions_per_tu)


def generate_preflight_reports(
    project_report: Any,
    *,
    baseline: BenchmarkResult,
    reports_dir: Path | None = None,
    rule_ids: list[str] | None = None,
) -> dict[str, Path]:
    """Write Phase 6.1 analyzer efficiency artifacts under ``reports/``."""
    from misra_platform_rules.registry import create_default_registry

    output_dir = reports_dir or (_TESTS_DIR.parent / "reports")
    cache_report = project_cache_report_from_execution(project_report, label=baseline.label)
    top_costs = build_top_analyzer_costs(
        cache_report["aggregate"],
        rule_timings=baseline.rule_timings_top_slowest,
    )
    if rule_ids is None:
        rule_ids = create_default_registry().list_rule_ids()
    reuse_report = build_reuse_report(rule_ids)
    return write_preflight_reports(
        output_dir,
        cache_report=cache_report,
        top_costs=top_costs,
        reuse_report=reuse_report,
    )


def generate_report(*, baseline_tus: int = 60, functions_per_tu: int = 40) -> dict[str, Any]:
    baseline, project_report = run_measured_project(
        translation_units=baseline_tus, functions_per_tu=functions_per_tu
    )

    projected_100k_seconds = extrapolate(baseline, 100_000)
    projected_500k_seconds = extrapolate(baseline, 500_000)

    incremental_tus = max(1, round(baseline_tus * 0.1))
    incremental, _ = run_incremental(baseline_tus, incremental_tus, functions_per_tu=functions_per_tu)
    incremental_fraction = incremental.duration_ms / baseline.duration_ms if baseline.duration_ms else 0.0

    generate_preflight_reports(project_report, baseline=baseline)

    return {
        "baseline": asdict(baseline),
        "measured_ms_per_loc": baseline.duration_ms / baseline.loc,
        "targets": {
            "100k_loc_seconds_budget": TARGET_100K_LOC_SECONDS,
            "500k_loc_seconds_budget": TARGET_500K_LOC_SECONDS,
            "incremental_fraction_budget": TARGET_INCREMENTAL_FRACTION,
        },
        "projections": {
            "100k_loc_projected_seconds": round(projected_100k_seconds, 2),
            "100k_loc_meets_target": projected_100k_seconds < TARGET_100K_LOC_SECONDS,
            "500k_loc_projected_seconds": round(projected_500k_seconds, 2),
            "500k_loc_meets_target": projected_500k_seconds < TARGET_500K_LOC_SECONDS,
        },
        "incremental": {
            **asdict(incremental),
            "fraction_of_baseline": round(incremental_fraction, 4),
            "meets_target": incremental_fraction < TARGET_INCREMENTAL_FRACTION,
        },
        "methodology": (
            "Synthetic-AST throughput extrapolation: no real 100K/500K LOC embedded "
            "C corpus or live clang-worker AST pipeline is available in this "
            "environment, so measured ms/LOC on a representative synthetic project "
            "is extrapolated linearly. Real-world figures will additionally include "
            "clang parsing time, network/IPC overhead to clang-worker, and I/O, none "
            "of which are modeled here. Treat these numbers as a rule-engine-only "
            "lower bound, not an end-to-end SLA."
        ),
    }


if __name__ == "__main__":
    report = generate_report()
    output_path = Path(__file__).with_name("performance_report.json")
    output_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
