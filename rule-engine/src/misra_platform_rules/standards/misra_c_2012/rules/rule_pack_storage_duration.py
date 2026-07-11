"""Storage Duration rule pack (Phase 3) — MISRA C:2012 Rules 8.9 and 18.6."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


def _enclosing_function_id(node: dict, graph: AstGraph) -> str | None:
    parent_id = node.get("parent_id", "")
    while parent_id:
        parent = graph.get(parent_id)
        if not parent:
            return None
        if parent.get("node_kind") == "FunctionDecl":
            return parent["node_id"]
        parent_id = parent.get("parent_id", "")
    return None


class Rule8_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-9",
            rule_number="8.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="An object should be defined at block scope if used in one function only",
            description="A file-scope object referenced from only one function should be moved to block scope.",
            rationale="File-scope objects used by a single function needlessly widen their visibility/lifetime.",
            tags=["storage-duration", "scope"],
            references=["MISRA C:2012 Rule 8.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_storage_duration",
            requires_ast_nodes=["VarDecl", "DeclRefExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STORAGE_DURATION,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for var_decl in graph.nodes_by_kind("VarDecl"):
            if not graph.is_file_scope(var_decl["node_id"]):
                continue
            storage = var_decl.get("semantic_properties", {}).get("storage_class", "")
            if storage == "extern":
                continue
            name = var_decl.get("semantic_properties", {}).get("name", "")
            if not name:
                continue
            references = [
                node
                for node in graph.all_nodes()
                if node.get("node_kind") == "DeclRefExpr"
                and node.get("semantic_properties", {}).get("name") == name
            ]
            if not references:
                continue
            enclosing_functions = {_enclosing_function_id(ref, graph) for ref in references}
            enclosing_functions.discard(None)
            if len(enclosing_functions) != 1:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    var_decl,
                    explanation=f"File-scope object '{name}' is referenced from a single function only.",
                    risk_description="Unnecessary file scope widens the object's visibility and lifetime.",
                    confidence_factors={
                        "ast_match_specificity": 0.75,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.68,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(var_decl),
                        suggested_code=f"move the definition of '{name}' inside the function that uses it",
                        rationale="Prefer the narrowest scope that satisfies the usage.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void process(void) {\n    static uint16_t cache = 0U;\n    /* ... */\n}"],
            non_compliant=["static uint16_t cache = 0U;\nvoid process(void) {\n    /* only user of cache */\n}"],
        )


class Rule18_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-18-6",
            rule_number="18.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The address of an automatic object shall not escape its lifetime",
            description="A function shall not return the address of one of its own automatic (local) objects.",
            rationale="The returned pointer is dangling as soon as the function returns.",
            tags=["storage-duration", "pointers"],
            references=["MISRA C:2012 Rule 18.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_storage_duration",
            requires_ast_nodes=["FunctionDecl", "ReturnStmt", "VarDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STORAGE_DURATION,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            descendants = graph.descendants(function_node["node_id"])
            local_names = {
                node.get("semantic_properties", {}).get("name", "")
                for node in descendants
                if node.get("node_kind") == "VarDecl"
                and node.get("semantic_properties", {}).get("storage_class", "automatic") == "automatic"
            }
            local_names.discard("")
            if not local_names:
                continue
            for return_stmt in [d for d in descendants if d.get("node_kind") == "ReturnStmt"]:
                return_descendants = graph.descendants(return_stmt["node_id"])
                escaped = pointers.returns_address_of_local(return_stmt, return_descendants, local_names)
                if not escaped:
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        return_stmt,
                        explanation=f"Function returns the address of automatic local variable '{escaped}'.",
                        risk_description="The returned pointer dangles as soon as the function returns.",
                        confidence_factors={
                            "ast_match_specificity": 0.92,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.08,
                            "fix_generator_certainty": 0.3,
                        },
                        confidence_score=0.88,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(return_stmt),
                            suggested_code=f"allocate '{escaped}' with static/heap/caller-provided storage instead",
                            rationale="The pointee must outlive the returning function.",
                            confidence_score=0.3,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void fill(uint8_t *out) {\n    *out = 1U;\n}"],
            non_compliant=["uint8_t *make(void) {\n    uint8_t local = 1U;\n    return &local;\n}"],
        )
