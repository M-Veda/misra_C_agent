import uuid
from typing import Any

from misra_platform_rules.analyzers import LinkageIndex
from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.fingerprint import generate_fingerprint
from misra_platform_rules.registry import RuleRegistry, create_default_registry
from misra_platform_rules.rule_context import PreviousViolation
from misra_platform_rules.worker_pool import WorkerPool, build_translation_unit_job

from misra_platform.core.config import Settings
from misra_platform.repositories.violation_repo import ViolationRepository

_CONFIDENCE_BUCKETS = [
    ("0.0-0.2", 0.0, 0.2),
    ("0.2-0.4", 0.2, 0.4),
    ("0.4-0.6", 0.4, 0.6),
    ("0.6-0.8", 0.6, 0.8),
    ("0.8-1.0", 0.8, 1.0001),
]


def _confidence_distribution(scores: list[float]) -> dict[str, int]:
    distribution = {label: 0 for label, _, _ in _CONFIDENCE_BUCKETS}
    for score in scores:
        for label, low, high in _CONFIDENCE_BUCKETS:
            if low <= score < high:
                distribution[label] += 1
                break
    return distribution


class RuleDispatcher:
    def __init__(self, settings: Settings, registry: RuleRegistry | None = None) -> None:
        self.settings = settings
        self.registry = registry or create_default_registry()
        self.worker_pool = WorkerPool(
            tu_workers=settings.rule_engine_tu_workers,
            rule_workers=settings.rule_engine_rule_workers,
            rule_timeout_seconds=settings.rule_engine_timeout_seconds,
        )

    def execute_for_translation_units(
        self,
        *,
        artifacts: list[dict[str, Any]],
        translation_unit_ids: list[uuid.UUID],
        toolchain_profile: dict[str, Any] | None,
        include_graph: dict[str, list[str]] | None,
        previous_violations: list[PreviousViolation] | None = None,
        enabled_rules: list[str] | None = None,
    ) -> dict[str, Any]:
        rules = self.registry.select_rules(enabled_rules)

        # Build the project-wide linkage index once, up front, so Category E
        # (cross-translation-unit) rules can see every TU's file-scope
        # declarations without re-parsing the whole project per-TU.
        cross_tu_linkage = LinkageIndex.build(
            [
                (str(tu_id), artifact.get("file_path", ""), AstGraph(artifact.get("nodes", [])))
                for artifact, tu_id in zip(artifacts, translation_unit_ids, strict=True)
            ]
        )

        jobs = [
            build_translation_unit_job(
                artifact=artifact,
                translation_unit_id=tu_id,
                rules=rules,
                include_graph=include_graph,
                toolchain_profile=toolchain_profile,
                previous_violations=previous_violations,
                cross_tu_linkage=cross_tu_linkage,
            )
            for artifact, tu_id in zip(artifacts, translation_unit_ids, strict=True)
        ]

        project_report = self.worker_pool.execute_project(jobs)
        all_violations: list[dict[str, Any]] = []
        all_metrics: list[dict[str, Any]] = []
        deduplicated_total = 0

        for tu_id, tu_report in project_report.translation_unit_reports.items():
            deduplicated_total += tu_report.deduplicated_count
            for violation in tu_report.violations:
                metadata = self.registry.get_metadata(violation.rule_id)
                fingerprint = generate_fingerprint(violation)
                all_violations.append(
                    {
                        "translation_unit_id": tu_id,
                        "rule_id": violation.rule_id,
                        "fingerprint": fingerprint,
                        "file_path": violation.file_path,
                        "line_start": violation.line_start,
                        "line_end": violation.line_end,
                        "column_start": violation.column_start,
                        "column_end": violation.column_end,
                        "severity": metadata.severity,
                        "confidence_score": violation.confidence_score,
                        "category": metadata.category,
                        "offending_expression": violation.offending_expression,
                        "explanation": violation.explanation,
                        "risk_description": violation.risk_description,
                        "source_snippet": violation.source_snippet,
                        "ast_node_reference": violation.ast_node_id,
                        "macro_expansion_chain": violation.macro_expansion_chain,
                        "suggested_fix": (
                            violation.suggested_fix.model_dump() if violation.suggested_fix else None
                        ),
                        "confidence_factors": violation.confidence_factors,
                    }
                )
            for metric in tu_report.metrics:
                all_metrics.append(
                    {
                        "translation_unit_id": tu_id,
                        "rule_id": metric.rule_id,
                        "duration_ms": metric.duration_ms,
                        "violation_count": metric.violation_count,
                        "success": metric.success,
                        "error_message": metric.error_message,
                    }
                )

        confidence_scores = [violation["confidence_score"] for violation in all_violations]
        per_rule_timing: dict[str, list[float]] = {}
        for metric in all_metrics:
            per_rule_timing.setdefault(metric["rule_id"], []).append(metric["duration_ms"])

        return {
            "violations": all_violations,
            "metrics": all_metrics,
            "statistics": {
                "rules_executed": len(rules) * len(artifacts),
                "violations_total": len(all_violations),
                "violations_deduplicated": deduplicated_total,
                "execution_duration_ms": project_report.total_duration_ms,
                "translation_units_analyzed": len(artifacts),
                "metrics_json": {
                    "per_rule": [
                        {
                            "rule_id": metric.rule_id,
                            "duration_ms": metric.duration_ms,
                            "violation_count": metric.violation_count,
                            "success": metric.success,
                        }
                        for metric in all_metrics
                    ],
                    # Phase 3 metrics: rule timing aggregates + confidence distribution.
                    "rule_timing_summary": {
                        rule_id: {
                            "total_ms": sum(durations),
                            "avg_ms": sum(durations) / len(durations),
                            "max_ms": max(durations),
                            "invocations": len(durations),
                        }
                        for rule_id, durations in per_rule_timing.items()
                    },
                    "confidence_distribution": _confidence_distribution(confidence_scores),
                    "false_positive_candidates": sum(
                        1 for score in confidence_scores if score < 0.6
                    ),
                },
            },
        }

    async def persist_results(
        self,
        repo: ViolationRepository,
        *,
        analysis_run_id: uuid.UUID,
        project_id: uuid.UUID,
        results: dict[str, Any],
    ) -> None:
        metrics_by_tu: dict[str | None, list[dict[str, Any]]] = {}
        for metric in results["metrics"]:
            tu_key = metric.get("translation_unit_id")
            metrics_by_tu.setdefault(tu_key, []).append(metric)

        violations_by_tu: dict[str | None, list[dict[str, Any]]] = {}
        for violation in results["violations"]:
            tu_key = violation.get("translation_unit_id")
            violations_by_tu.setdefault(tu_key, []).append(violation)

        for tu_key, violations in violations_by_tu.items():
            tu_uuid = uuid.UUID(tu_key) if tu_key else None
            await repo.upsert_violations(
                analysis_run_id=analysis_run_id,
                project_id=project_id,
                translation_unit_id=tu_uuid,
                violations=violations,
            )

        for tu_key, metrics in metrics_by_tu.items():
            tu_uuid = uuid.UUID(tu_key) if tu_key else None
            await repo.save_execution_metrics(
                analysis_run_id=analysis_run_id,
                translation_unit_id=tu_uuid,
                metrics=metrics,
            )

        await repo.save_run_statistics(
            analysis_run_id=analysis_run_id,
            statistics=results["statistics"],
        )
