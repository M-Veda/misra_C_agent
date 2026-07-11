"""Phase 6: shared analyzer caching.

Before this module, every rule that needed a function's CFG, alias facts,
symbol index, or linkage facts computed them itself — `Rule2_1`, `Rule9_1`,
`Rule17_4`, and `Rule15_4` each independently called
`CFGEngine().build(function_node, graph)` for the *same* function within
the *same* translation-unit run, redoing identical basic-block construction
four times over. `AnalysisCache` fixes that by memoizing the expensive,
purely-a-function-of-(function/graph) shared-analyzer results for the
lifetime of one `RuleContext` (one translation unit, one run) so that no
matter how many rules ask for a given function's CFG, it is built exactly
once.

Scope: one `AnalysisCache` per `RuleContext` (see `RuleContext.analysis_cache`,
created lazily in `__post_init__`). Since `RuleExecutionEngine.execute()`
passes the *same* `RuleContext` instance to every rule plugin run against a
translation unit, this cache is naturally scoped to exactly "one run over
one translation unit" — long enough to deduplicate across rules, short
enough that nothing leaks between translation units or between test cases
(`RuleContext.from_ast_artifact()` always builds a fresh context, hence a
fresh, empty cache).

Cached entries are keyed by AST node id (per-function analyses) or are
singletons (per-translation-unit analyses like the symbol/linkage index),
never by rule id — the whole point is that the *same* answer is shared
across every rule that asks the same question.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from misra_platform_rules.analyzer_efficiency import (
    MISS_REASON_FIRST_ACCESS,
)
from misra_platform_rules.analyzers.alias_analyzer import AliasAnalyzer
from misra_platform_rules.analyzers.cfg_engine import CFGEngine, ControlFlowGraph
from misra_platform_rules.analyzers.dataflow_engine_v2 import DataFlowEngineV2
from misra_platform_rules.analyzers.linkage_analyzer import LinkageAnalyzer
from misra_platform_rules.analyzers.linkage_index import LinkageIndex
from misra_platform_rules.analyzers.symbol_index import SymbolIndex

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph


class AnalysisCache:
    def __init__(self) -> None:
        self._cfg: dict[str, ControlFlowGraph] = {}
        self._alias: dict[str, AliasAnalyzer] = {}
        self._dataflow_engine: dict[str, DataFlowEngineV2] = {}
        self._dataflow_results: dict[tuple[str, str], Any] = {}
        self._symbol_index: SymbolIndex | None = None
        self._linkage_index: LinkageIndex | None = None
        self._linkage_analyzer: LinkageAnalyzer | None = None
        self.hits = 0
        self.misses = 0
        self._hits_by_analyzer: dict[str, int] = defaultdict(int)
        self._misses_by_analyzer: dict[str, int] = defaultdict(int)
        self._miss_reasons: dict[str, int] = defaultdict(int)
        self._cfg_builds_per_function: dict[str, int] = defaultdict(int)
        self._alias_builds_per_function: dict[str, int] = defaultdict(int)
        self._dataflow_builds_per_function: dict[str, int] = defaultdict(int)
        self._symbol_index_builds = 0
        self._linkage_index_builds = 0
        self._linkage_analyzer_builds = 0

    def _record_hit(self, analyzer: str) -> None:
        self.hits += 1
        self._hits_by_analyzer[analyzer] += 1

    def _record_miss(self, analyzer: str, reason: str) -> None:
        self.misses += 1
        self._misses_by_analyzer[analyzer] += 1
        self._miss_reasons[reason] += 1

    def cfg(self, function_node: dict[str, Any], graph: "AstGraph") -> ControlFlowGraph:
        key = function_node["node_id"]
        cached = self._cfg.get(key)
        if cached is not None:
            self._record_hit("cfg")
            return cached
        self._record_miss("cfg", f"cfg:{MISS_REASON_FIRST_ACCESS}")
        result = CFGEngine().build(function_node, graph)
        self._cfg[key] = result
        self._cfg_builds_per_function[key] += 1
        return result

    def aliases(self, function_node: dict[str, Any], graph: "AstGraph") -> AliasAnalyzer:
        key = function_node["node_id"]
        cached = self._alias.get(key)
        if cached is not None:
            self._record_hit("alias")
            return cached
        self._record_miss("alias", f"alias:{MISS_REASON_FIRST_ACCESS}")
        result = AliasAnalyzer().analyze(function_node, graph)
        self._alias[key] = result
        self._alias_builds_per_function[key] += 1
        return result

    def dataflow_engine(self, function_node: dict[str, Any], graph: "AstGraph") -> DataFlowEngineV2:
        key = function_node["node_id"]
        cached = self._dataflow_engine.get(key)
        if cached is not None:
            self._record_hit("dataflow_engine")
            return cached
        self._record_miss("dataflow_engine", f"dataflow_engine:{MISS_REASON_FIRST_ACCESS}")
        alias = self.aliases(function_node, graph)
        result = DataFlowEngineV2(alias)
        self._dataflow_engine[key] = result
        self._dataflow_builds_per_function[key] += 1
        return result

    def dataflow_result(self, function_node: dict[str, Any], analysis_name: str, compute: Any) -> Any:
        """Memoizes the result of an arbitrary dataflow query (e.g.
        `uninitialized_reads`, `reaching_definitions`) for a given function,
        so a second rule asking the exact same question about the exact
        same function gets the cached answer instead of re-running the
        worklist algorithm. `compute` is a zero-arg callable invoked only on
        a cache miss."""
        key = (function_node["node_id"], analysis_name)
        if key in self._dataflow_results:
            self._record_hit("dataflow_result")
            return self._dataflow_results[key]
        self._record_miss("dataflow_result", f"dataflow_result:{MISS_REASON_FIRST_ACCESS}")
        result = compute()
        self._dataflow_results[key] = result
        return result

    def symbols(self, graph: "AstGraph") -> SymbolIndex:
        if self._symbol_index is not None:
            self._record_hit("symbol_index")
            return self._symbol_index
        self._record_miss("symbol_index", f"symbol_index:{MISS_REASON_FIRST_ACCESS}")
        self._symbol_index = SymbolIndex(graph)
        self._symbol_index_builds += 1
        return self._symbol_index

    def linkage_index(self, cross_tu_linkage: dict[str, Any]) -> LinkageIndex:
        if self._linkage_index is not None:
            self._record_hit("linkage_index")
            return self._linkage_index
        self._record_miss("linkage_index", f"linkage_index:{MISS_REASON_FIRST_ACCESS}")
        self._linkage_index = LinkageIndex(cross_tu_linkage)
        self._linkage_index_builds += 1
        return self._linkage_index

    def linkage_analyzer(self, linkage_index: LinkageIndex) -> LinkageAnalyzer:
        if self._linkage_analyzer is not None:
            self._record_hit("linkage_analyzer")
            return self._linkage_analyzer
        self._record_miss("linkage_analyzer", f"linkage_analyzer:{MISS_REASON_FIRST_ACCESS}")
        self._linkage_analyzer = LinkageAnalyzer(linkage_index)
        self._linkage_analyzer_builds += 1
        return self._linkage_analyzer

    def efficiency_stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "hits_by_analyzer": dict(self._hits_by_analyzer),
            "misses_by_analyzer": dict(self._misses_by_analyzer),
            "hit_rates_by_analyzer": {
                analyzer: round(self._hits_by_analyzer[analyzer] / total_for, 4)
                if (total_for := self._hits_by_analyzer[analyzer] + self._misses_by_analyzer[analyzer])
                else 0.0
                for analyzer in set(self._hits_by_analyzer) | set(self._misses_by_analyzer)
            },
            "miss_reasons": dict(self._miss_reasons),
            "cfg_builds_per_function": dict(self._cfg_builds_per_function),
            "alias_builds_per_function": dict(self._alias_builds_per_function),
            "dataflow_builds_per_function": dict(self._dataflow_builds_per_function),
            "symbol_index_builds": self._symbol_index_builds,
            "linkage_index_builds": self._linkage_index_builds,
            "linkage_analyzer_builds": self._linkage_analyzer_builds,
            "cfgs_built": len(self._cfg),
            "alias_analyses_run": len(self._alias),
            "dataflow_engines_built": len(self._dataflow_engine),
        }

    def stats(self) -> dict[str, Any]:
        """Backward-compatible summary; prefer ``efficiency_stats()`` for reports."""
        return self.efficiency_stats()
