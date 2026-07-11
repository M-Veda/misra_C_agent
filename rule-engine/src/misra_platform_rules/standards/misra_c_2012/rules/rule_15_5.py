"""MISRA C:2012 Rule 15.5 — function should have a single point of exit."""

from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


class Rule15_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-5",
            rule_number="15.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A function should have a single point of exit at the end",
            description="Functions should contain a single return at the end of the function body.",
            rationale="Multiple exit points complicate control-flow reasoning and testing.",
            tags=["control-flow", "functions"],
            references=["MISRA C:2012 Rule 15.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_15_5",
            requires_ast_nodes=["FunctionDecl", "ReturnStmt"],
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("FunctionDecl"):
            body_nodes = [
                child for child in graph.children(node["node_id"]) if child.get("node_kind") == "CompoundStmt"
            ]
            if not body_nodes:
                continue
            body = body_nodes[0]
            return_stmts = [
                descendant
                for descendant in graph.descendants(body["node_id"])
                if descendant.get("node_kind") == "ReturnStmt"
            ]
            if len(return_stmts) <= 1:
                continue
            name = node.get("semantic_properties", {}).get("name", "<anonymous>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Function '{name}' has {len(return_stmts)} return statements; "
                        "a single exit point is recommended."
                    ),
                    risk_description="Multiple exits increase cyclomatic complexity and review burden.",
                    confidence_factors={
                        "ast_match_specificity": 0.98,
                        "type_information_complete": 0.95,
                        "macro_clarity": 0.98,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.84,
                    suggested_fix=SuggestedFix(
                        original_code=f"function {name}",
                        suggested_code="refactor to single return at end of function",
                        rationale="Consolidate exit logic to improve maintainability.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=[
                "uint8_t fn(uint8_t x) {\n    uint8_t result = 0U;\n    if (x > 0U) { result = 1U; }\n    return result;\n}"
            ],
            non_compliant=[
                "uint8_t fn(uint8_t x) {\n    if (x == 0U) { return 0U; }\n    return 1U;\n}"
            ],
        )
