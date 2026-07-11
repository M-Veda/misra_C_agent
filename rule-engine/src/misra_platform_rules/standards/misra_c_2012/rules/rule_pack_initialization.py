"""Initialization rule pack — MISRA C:2012 Rules 9.1 and 2.2.

Rule 9.1 (Phase 4) now runs on the real CFG-based `DataFlowEngineV2`: a
sound (may-analysis) reaching-definitions computation that catches
uninitialized reads reachable via *any* incoming path, including ones the
Phase 3 `DataFlowEngine` missed because it only ever checked the first
textual reference (e.g. `if (c) { x = 1; } use(x);` — uninitialized on the
`!c` path, but Phase 3's single first-reference check couldn't see that).

Rule 2.2 still uses the Phase 3 `DataFlowEngine` approximation — see that
module's docstring for the documented limitations."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


class Rule9_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-9-1",
            rule_number="9.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="Automatic objects shall be initialized before use",
            description="An object with automatic storage duration shall not be read before it is initialized.",
            rationale="Reading an uninitialized automatic object is undefined behaviour.",
            tags=["initialization", "dataflow"],
            references=["MISRA C:2012 Rule 9.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_initialization",
            requires_ast_nodes=["FunctionDecl", "VarDecl", "DeclRefExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.INITIALIZATION,
            requires_dataflow=True,
            requires_cfg=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            cfg = self.cfg_v2(function_node, graph, context)
            dataflow_v2 = self.dataflow_v2(function_node=function_node, graph=graph, context=context)
            for read in dataflow_v2.uninitialized_reads(function_node, cfg, graph):
                name = read.get("semantic_properties", {}).get("name", "<var>")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        read,
                        explanation=f"'{name}' is read before it is initialized on at least "
                        "one reachable path.",
                        risk_description="Reading an uninitialized automatic variable is undefined behaviour.",
                        confidence_factors={
                            "ast_match_specificity": 0.8,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.25,
                            "fix_generator_certainty": 0.5,
                        },
                        confidence_score=0.72,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(read),
                            suggested_code=f"initialize '{name}' at its declaration",
                            rationale="Give the variable a well-defined value before first use.",
                            confidence_score=0.5,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t total = 0U;\ntotal += next_value();"],
            non_compliant=["uint16_t total;\ntotal += next_value(); /* read before init */"],
        )


class Rule2_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-2",
            rule_number="2.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MINOR,
            title="There shall be no dead code",
            description="A value computed and stored shall be used at least once afterwards.",
            rationale="Dead stores indicate a logic error or leftover debugging code.",
            tags=["dataflow", "unused-code"],
            references=["MISRA C:2012 Rule 2.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_initialization",
            requires_ast_nodes=["FunctionDecl", "VarDecl", "DeclRefExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.INITIALIZATION,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        dataflow = self.dataflow()
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            for var_decl in dataflow.local_variable_declarations(function_node, graph):
                references = dataflow.references(var_decl, function_node, graph)
                if len(references) < 2:
                    continue  # a single write with no reads at all is more likely just unused
                dead = dataflow.dead_store(var_decl, function_node, graph)
                if dead is None:
                    continue
                name = var_decl.get("semantic_properties", {}).get("name", "<var>")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        dead,
                        explanation=f"Value stored into '{name}' here is never subsequently read.",
                        risk_description="Dead stores often indicate a missing use or a stale code path.",
                        confidence_factors={
                            "ast_match_specificity": 0.7,
                            "type_information_complete": 0.65,
                            "macro_clarity": 0.8,
                            "historical_false_positive_rate": 0.3,
                            "fix_generator_certainty": 0.3,
                        },
                        confidence_score=0.62,
                        suggested_fix=None,
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["result = compute();\nlog_value(result);"],
            non_compliant=["result = compute();\nresult = compute_again(); /* first store never read */"],
        )


def _initializer_indices(init_list: dict, graph: AstGraph) -> list[tuple[int, dict]]:
    """Resolves the effective array index of every child of an
    `InitListExpr`: an explicit `designator_index` (`[N] = ...`) if present,
    otherwise the next position after the previous element — shared by
    Rule9_3 and Rule9_5 so this positional/designator bookkeeping is defined
    exactly once."""
    resolved: list[tuple[int, dict]] = []
    next_index = 0
    for child in graph.children(init_list["node_id"]):
        designator = child.get("semantic_properties", {}).get("designator_index")
        index = designator if designator is not None else next_index
        resolved.append((index, child))
        next_index = index + 1
    return resolved


class Rule9_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-9-3",
            rule_number="9.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Array elements shall not be initialized more than once",
            description="No array index shall be targeted by more than one initializer in the "
            "same initializer list.",
            rationale="A repeated index means the earlier initializer's value is silently "
            "discarded, which is almost always a mistake.",
            tags=["initialization", "arrays"],
            references=["MISRA C:2012 Rule 9.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_initialization",
            requires_ast_nodes=["InitListExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.INITIALIZATION,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for init_list in graph.nodes_by_kind("InitListExpr"):
            if not init_list.get("semantic_properties", {}).get("is_array_initializer"):
                continue
            seen: dict[int, dict] = {}
            for index, child in _initializer_indices(init_list, graph):
                first = seen.get(index)
                if first is None:
                    seen[index] = child
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        child,
                        explanation=f"Array element [{index}] is initialized more than once in "
                        "this initializer list.",
                        risk_description="The earlier initializer's value is silently discarded, "
                        "which is almost always a mistake.",
                        confidence_factors={
                            "ast_match_specificity": 0.9,
                            "type_information_complete": 0.8,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.85,
                        suggested_fix=SuggestedFix(
                            original_code=f"[{index}] = ...",
                            suggested_code=f"remove the duplicate initializer for index {index}",
                            rationale="Each array index should be initialized exactly once.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t values[3] = { [0] = 1, [1] = 2, [2] = 3 };"],
            non_compliant=["int32_t values[3] = { [0] = 1, [0] = 2, [2] = 3 }; /* index 0 twice */"],
        )


class Rule9_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-9-5",
            rule_number="9.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="Designated initializers should not be mixed with non-designated for the same array",
            description="An array initializer list should use either all designated or all "
            "positional initializers, not a mix of both.",
            rationale="Mixing designated and positional initializers in one list makes the "
            "resulting index of every element hard to read at a glance.",
            tags=["initialization", "arrays"],
            references=["MISRA C:2012 Rule 9.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_initialization",
            requires_ast_nodes=["InitListExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.INITIALIZATION,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for init_list in graph.nodes_by_kind("InitListExpr"):
            if not init_list.get("semantic_properties", {}).get("is_array_initializer"):
                continue
            children = graph.children(init_list["node_id"])
            designated = [c for c in children if c.get("semantic_properties", {}).get("designator_index") is not None]
            positional = [c for c in children if c.get("semantic_properties", {}).get("designator_index") is None]
            if not designated or not positional:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    init_list,
                    explanation=f"This array initializer list mixes {len(designated)} designated "
                    f"and {len(positional)} non-designated initializer(s).",
                    risk_description="Mixing designated and positional initializers makes the "
                    "resulting index of every element hard to read at a glance.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.7,
                    suggested_fix=SuggestedFix(
                        original_code="{ [0] = 1, 2, 3 }",
                        suggested_code="use either all designated ({ [0] = 1, [1] = 2, [2] = 3 }) "
                        "or all positional ({ 1, 2, 3 }) initializers",
                        rationale="Do not mix designated and positional initializers in one list.",
                        confidence_score=0.3,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t values[3] = { 1, 2, 3 };"],
            non_compliant=["int32_t values[3] = { [0] = 1, 2, 3 }; /* mixes designated and positional */"],
        )
