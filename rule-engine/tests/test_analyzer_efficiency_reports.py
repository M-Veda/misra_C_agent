"""Phase 6.1 preflight metrics: analyzer efficiency report generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from misra_platform_rules import analyzer_reuse
from misra_platform_rules.analyzer_efficiency import (
    aggregate_tu_efficiency_stats,
    build_reuse_report,
    build_top_analyzer_costs,
    project_cache_report_from_execution,
    write_preflight_reports,
)
from misra_platform_rules.analyzers import LinkageIndex
from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.conformance import ConformanceRunner
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.worker_pool import WorkerPool, build_translation_unit_job

from conformance.fixtures import build_all_suites

perf_dir = Path(__file__).resolve().parent / "performance"
sys.path.insert(0, str(perf_dir))
from synthetic_project import build_project  # noqa: E402

_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _function_fixture() -> dict:
    return {
        "file_path": "demo.c",
        "nodes": [
            {
                "node_id": "fn",
                "node_kind": "FunctionDecl",
                "parent_id": "",
                "children_ids": ["body"],
                "source_range": {"line_start": 1, "line_end": 5},
                "semantic_properties": {"name": "compute"},
                "essential_type": "signed_int",
            },
            {
                "node_id": "body",
                "node_kind": "CompoundStmt",
                "parent_id": "fn",
                "children_ids": ["ret"],
                "source_range": {"line_start": 1, "line_end": 5},
                "semantic_properties": {},
            },
            {
                "node_id": "ret",
                "node_kind": "ReturnStmt",
                "parent_id": "body",
                "children_ids": [],
                "source_range": {"line_start": 2, "line_end": 2},
                "semantic_properties": {},
            },
        ],
        "diagnostics": [],
        "preprocessor": {},
    }


def test_analysis_cache_tracks_builds_per_semantic_unit() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_fixture(), translation_unit_id="tu-1")
    graph = AstGraph(context.ast_nodes)
    function_node = graph.get("fn")
    cache = context.analysis_cache

    cache.cfg(function_node, graph)
    cache.cfg(function_node, graph)
    cache.aliases(function_node, graph)
    cache.dataflow_engine(function_node, graph)
    cache.dataflow_engine(function_node, graph)
    cache.symbols(graph)
    cache.symbols(graph)
    cache.linkage_index({})

    stats = cache.efficiency_stats()
    assert stats["cfg_builds_per_function"]["fn"] == 1
    assert stats["alias_builds_per_function"]["fn"] == 1
    assert stats["dataflow_builds_per_function"]["fn"] == 1
    assert stats["symbol_index_builds"] == 1
    assert stats["linkage_index_builds"] == 1
    assert "cfg:first_access_for_semantic_unit" in stats["miss_reasons"]
    assert stats["hits"] >= 4


def test_aggregate_efficiency_stats_enforces_semantic_budgets() -> None:
    compliant = {
        "cfg_builds_per_function": {"fn-a": 1, "fn-b": 1},
        "alias_builds_per_function": {"fn-a": 1},
        "dataflow_builds_per_function": {"fn-a": 1},
        "symbol_index_builds": 1,
        "linkage_index_builds": 1,
        "hits": 10,
        "misses": 5,
        "hits_by_analyzer": {"cfg": 8},
        "misses_by_analyzer": {"cfg": 2},
        "miss_reasons": {"cfg:first_access_for_semantic_unit": 2},
    }
    agg = aggregate_tu_efficiency_stats([compliant, compliant])
    assert agg["all_budgets_met"] is True
    assert agg["cfgs_built"] == 4

    violating = {**compliant, "cfg_builds_per_function": {"fn-a": 2}}
    agg_bad = aggregate_tu_efficiency_stats([violating])
    assert agg_bad["semantic_unit_budgets"]["cfg"]["compliant"] is False


def test_preflight_reports_written() -> None:
    project = build_project(translation_units=3, functions_per_tu=5)
    registry = create_default_registry()
    rules = registry.select_rules(None)
    linkage = LinkageIndex.build(
        [
            (str(index), artifact.get("file_path", ""), AstGraph(artifact.get("nodes", [])))
            for index, artifact in enumerate(project.artifacts)
        ]
    )
    jobs = [
        build_translation_unit_job(
            artifact=artifact,
            translation_unit_id=str(index),
            rules=rules,
            cross_tu_linkage=linkage,
        )
        for index, artifact in enumerate(project.artifacts)
    ]
    project_report = WorkerPool(tu_workers=2, rule_workers=2).execute_project(jobs)

    cache_report = project_cache_report_from_execution(
        project_report,
        label=f"{project.loc_total} LOC synthetic preflight",
    )
    top_costs = build_top_analyzer_costs(cache_report["aggregate"])

    analyzer_reuse.reset()
    runner = ConformanceRunner()
    suites = build_all_suites()
    plugins = {rule_id: registry.get(rule_id) for rule_id in registry.list_rule_ids()}
    for suite in suites:
        runner.run(plugins[suite.rule_id], suite)
    reuse_report = build_reuse_report(sorted(plugins.keys()))

    paths = write_preflight_reports(
        _REPORTS_DIR,
        cache_report=cache_report,
        top_costs=top_costs,
        reuse_report=reuse_report,
    )

    for path in paths.values():
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload

    assert cache_report["all_semantic_unit_budgets_met"] is True
    assert "cache_hit_ratios" in cache_report
    assert "cache_miss_reasons" in cache_report
    assert top_costs["ranked_by_analyzer_cost"]
    assert reuse_report["reuse_percentage"] == pytest.approx(100.0, abs=0.1)
