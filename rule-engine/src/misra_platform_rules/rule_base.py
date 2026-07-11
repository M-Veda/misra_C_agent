from abc import ABC, abstractmethod

from misra_platform_rules import analyzer_reuse
from misra_platform_rules.analyzers import (
    AliasAnalyzer,
    CastAnalyzer,
    CFGBuilder,
    CFGEngine,
    ControlFlowGraph,
    DataFlowEngine,
    DataFlowEngineV2,
    EssentialTypeAnalyzer,
    EssentialTypeEngine,
    ExpressionClassifier,
    LinkageAnalyzer,
    LinkageIndex,
    MacroAnalyzer,
    PointerAnalyzer,
    QualifierAnalyzer,
    SymbolIndex,
)
from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


class BaseRulePlugin(ABC):
    @property
    @abstractmethod
    def metadata(self) -> RuleMetadata: ...

    @abstractmethod
    def detect(self, context: RuleContext) -> list[RuleResult]: ...

    def explain(self, result: RuleResult) -> str:
        return result.explanation

    def generate_fix(self, result: RuleResult) -> SuggestedFix | None:
        return result.suggested_fix

    def examples(self) -> RuleExamples:
        return RuleExamples()

    def graph(self, context: RuleContext) -> AstGraph:
        self._record_analyzer_usage("graph")
        return AstGraph(context.ast_nodes)

    def _record_analyzer_usage(self, analyzer_name: str) -> None:
        """Records that this rule invoked a shared analyzer accessor.

        Every accessor below calls this before returning, so that reuse can
        be *measured* (see `analyzer_reuse.py`) rather than merely asserted
        by policy. Never fails the rule if metadata access is unexpectedly
        unavailable -- reuse tracking must not affect detection behavior.
        """
        try:
            rule_id = self.metadata.rule_id
        except Exception:
            return
        analyzer_reuse.record_usage(rule_id, analyzer_name)

    # Shared analysis infrastructure (Phase 3). Rules call these instead of
    # duplicating essential-type / cast / pointer / CFG / dataflow logic.
    def essential_types(self) -> EssentialTypeAnalyzer:
        self._record_analyzer_usage("essential_types")
        return EssentialTypeAnalyzer()

    def casts(self) -> CastAnalyzer:
        self._record_analyzer_usage("casts")
        return CastAnalyzer(EssentialTypeAnalyzer())

    def pointers(self) -> PointerAnalyzer:
        self._record_analyzer_usage("pointers")
        return PointerAnalyzer()

    def qualifiers(self) -> QualifierAnalyzer:
        self._record_analyzer_usage("qualifiers")
        return QualifierAnalyzer()

    def cfg(self) -> CFGBuilder:
        self._record_analyzer_usage("cfg")
        return CFGBuilder()

    def dataflow(self) -> DataFlowEngine:
        self._record_analyzer_usage("dataflow")
        return DataFlowEngine()

    def symbols(self, graph: AstGraph, context: RuleContext | None = None) -> SymbolIndex:
        self._record_analyzer_usage("symbols")
        if context is not None and context.analysis_cache is not None:
            return context.analysis_cache.symbols(graph)
        return SymbolIndex(graph)

    def linkage(self, context: RuleContext) -> LinkageIndex:
        self._record_analyzer_usage("linkage")
        if context.analysis_cache is not None:
            return context.analysis_cache.linkage_index(context.cross_tu_linkage)
        return LinkageIndex(context.cross_tu_linkage)

    def macros(self) -> MacroAnalyzer:
        self._record_analyzer_usage("macros")
        return MacroAnalyzer()

    def expressions(self) -> ExpressionClassifier:
        self._record_analyzer_usage("expressions")
        return ExpressionClassifier()

    # Shared analysis infrastructure (Phase 4). Real CFG-based dataflow,
    # alias analysis, the v2 essential-type engine, and ODR-style linkage
    # checks. Prefer these over the Phase 3 structural approximations
    # (`cfg()`/`dataflow()` above) whenever a rule needs sound flow facts.
    def cfg_v2(self, function_node: dict, graph: AstGraph, context: RuleContext | None = None) -> ControlFlowGraph:
        self._record_analyzer_usage("cfg_v2")
        if context is not None and context.analysis_cache is not None:
            return context.analysis_cache.cfg(function_node, graph)
        return CFGEngine().build(function_node, graph)

    def dataflow_v2(
        self,
        alias_analyzer: AliasAnalyzer | None = None,
        *,
        function_node: dict | None = None,
        graph: AstGraph | None = None,
        context: RuleContext | None = None,
    ) -> DataFlowEngineV2:
        self._record_analyzer_usage("dataflow_v2")
        if context is not None and context.analysis_cache is not None and function_node is not None and graph is not None:
            return context.analysis_cache.dataflow_engine(function_node, graph)
        return DataFlowEngineV2(alias_analyzer)

    def aliases(self, function_node: dict, graph: AstGraph, context: RuleContext | None = None) -> AliasAnalyzer:
        self._record_analyzer_usage("aliases")
        if context is not None and context.analysis_cache is not None:
            return context.analysis_cache.aliases(function_node, graph)
        return AliasAnalyzer().analyze(function_node, graph)

    def essential_types_v2(self) -> EssentialTypeEngine:
        self._record_analyzer_usage("essential_types_v2")
        return EssentialTypeEngine()

    def linkage_analyzer(self, context: RuleContext) -> LinkageAnalyzer:
        self._record_analyzer_usage("linkage_analyzer")
        if context.analysis_cache is not None:
            return context.analysis_cache.linkage_analyzer(self.linkage(context))
        return LinkageAnalyzer(self.linkage(context))

    def make_result(
        self,
        context: RuleContext,
        graph: AstGraph,
        node: dict,
        *,
        explanation: str,
        risk_description: str,
        confidence_factors: dict[str, float],
        confidence_score: float,
        suggested_fix: SuggestedFix | None = None,
    ) -> RuleResult:
        source_range = node.get("source_range", {})
        node_id = node["node_id"]
        macro_origin = node.get("macro_origin", {})
        return RuleResult(
            rule_id=self.metadata.rule_id,
            file_path=source_range.get("file_path", context.file_path),
            line_start=source_range.get("line_start", 0),
            line_end=source_range.get("line_end", 0),
            column_start=source_range.get("column_start", 0),
            column_end=source_range.get("column_end", 0),
            offending_expression=AstGraph.offending_text(node),
            explanation=explanation,
            risk_description=risk_description,
            source_snippet=graph.source_snippet(context, node),
            ast_node_id=node_id,
            ast_node_path=graph.node_path(node_id),
            macro_expansion_chain=list(macro_origin.get("expansion_chain", [])),
            confidence_score=confidence_score,
            suggested_fix=suggested_fix,
            confidence_factors=confidence_factors,
        )
