from misra_platform_rules.analysis_cache import AnalysisCache
from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_context import RuleContext


def _function_with_dead_code() -> dict:
    nodes = [
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
            "children_ids": ["ret", "dead"],
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
        {
            "node_id": "dead",
            "node_kind": "VarDecl",
            "parent_id": "body",
            "children_ids": [],
            "source_range": {"line_start": 3, "line_end": 3},
            "semantic_properties": {"name": "unused"},
        },
    ]
    return {"file_path": "demo.c", "nodes": nodes, "diagnostics": [], "preprocessor": {}}


def test_context_gets_a_fresh_analysis_cache_by_default() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    assert isinstance(context.analysis_cache, AnalysisCache)
    assert context.analysis_cache.hits == 0
    assert context.analysis_cache.misses == 0


def test_two_contexts_get_independent_caches() -> None:
    a = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-a")
    b = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-b")
    assert a.analysis_cache is not b.analysis_cache


def test_cfg_is_built_once_and_reused_across_calls() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    graph = AstGraph(context.ast_nodes)
    function_node = graph.get("fn")

    first = context.analysis_cache.cfg(function_node, graph)
    second = context.analysis_cache.cfg(function_node, graph)

    assert first is second
    assert context.analysis_cache.misses == 1
    assert context.analysis_cache.hits == 1


def test_aliases_and_dataflow_engine_are_cached_per_function() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    graph = AstGraph(context.ast_nodes)
    function_node = graph.get("fn")

    a1 = context.analysis_cache.aliases(function_node, graph)
    a2 = context.analysis_cache.aliases(function_node, graph)
    assert a1 is a2

    engine1 = context.analysis_cache.dataflow_engine(function_node, graph)
    engine2 = context.analysis_cache.dataflow_engine(function_node, graph)
    assert engine1 is engine2


def test_symbol_index_and_linkage_are_singletons_per_context() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    graph = AstGraph(context.ast_nodes)

    s1 = context.analysis_cache.symbols(graph)
    s2 = context.analysis_cache.symbols(graph)
    assert s1 is s2

    l1 = context.analysis_cache.linkage_index({})
    l2 = context.analysis_cache.linkage_index({})
    assert l1 is l2

    la1 = context.analysis_cache.linkage_analyzer(l1)
    la2 = context.analysis_cache.linkage_analyzer(l2)
    assert la1 is la2


def test_dataflow_result_memoizes_by_function_and_analysis_name() -> None:
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    graph = AstGraph(context.ast_nodes)
    function_node = graph.get("fn")

    calls = {"count": 0}

    def compute() -> list[str]:
        calls["count"] += 1
        return ["result"]

    first = context.analysis_cache.dataflow_result(function_node, "uninitialized_reads", compute)
    second = context.analysis_cache.dataflow_result(function_node, "uninitialized_reads", compute)

    assert first == ["result"]
    assert second == ["result"]
    assert calls["count"] == 1  # compute() only invoked on the miss


def test_real_multi_rule_run_builds_each_function_cfg_exactly_once() -> None:
    """End-to-end proof, not just a unit test of `AnalysisCache` in
    isolation: running the *actual* registered CFG-consuming rules
    (2.1 unreachable code, 9.1 uninitialized reads, 17.4 explicit return,
    15.4 single break/goto) against one function must build that function's
    CFG exactly once, not once per rule."""
    registry = create_default_registry()
    cfg_rule_ids = [
        "misra-c2012-rule-2-1",
        "misra-c2012-rule-9-1",
        "misra-c2012-rule-17-4",
        "misra-c2012-rule-15-4",
    ]
    rules = [registry.get(rule_id) for rule_id in cfg_rule_ids]

    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    for rule in rules:
        rule.detect(context)

    stats = context.analysis_cache.stats()
    # Exactly one FunctionDecl in the fixture -> exactly one CFG built via
    # `cfg_v2()`/`AnalysisCache`, no matter how many of these rules ask for
    # it (2.1 and 9.1 use `cfg_v2()`; 17.4 does too; 15.4 still uses the
    # Phase 3 `CFGBuilder` structural approximation via `self.cfg()`, which
    # is a separate, uncached code path by design -- not part of this
    # cache's contract).
    assert stats["cfgs_built"] == 1
    assert context.analysis_cache.hits >= 2


def test_execution_report_includes_cache_hit_ratios() -> None:
    """Integrity requirement: analyzer cache hit ratios must be reported,
    not only tracked internally."""
    from misra_platform_rules.engine import RuleExecutionEngine

    registry = create_default_registry()
    rules = [
        registry.get("misra-c2012-rule-2-1"),
        registry.get("misra-c2012-rule-9-1"),
        registry.get("misra-c2012-rule-17-4"),
    ]
    context = RuleContext.from_ast_artifact(artifact=_function_with_dead_code(), translation_unit_id="tu-1")
    report = RuleExecutionEngine(max_workers=1).execute(context, rules)

    assert report.cache_stats is not None
    assert "hit_rate" in report.cache_stats
    assert "hits" in report.cache_stats
    assert "misses" in report.cache_stats
    assert report.cache_stats["cfgs_built"] == 1
    assert report.cache_stats["hits"] >= 1
