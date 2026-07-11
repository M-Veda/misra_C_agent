"""MISRA C:2012 Rule 10.3 — value shall not be assigned to a narrower essential type."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


class Rule10_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-3",
            rule_number="10.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Value shall not be assigned to an object with a narrower essential type",
            description=(
                "The value of an expression shall not be assigned to an object with a "
                "narrower essential type."
            ),
            rationale="Narrowing assignments can silently truncate values in embedded systems.",
            tags=["essential-types", "assignment"],
            references=["MISRA C:2012 Rule 10.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_10_3",
            requires_ast_nodes=["BinaryOperator", "VarDecl"],
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            operator = node.get("semantic_properties", {}).get("opcode", "")
            if operator != "=":
                continue
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            lhs_type = children[0].get("essential_type", "unknown")
            rhs_type = children[1].get("essential_type", "unknown")
            if lhs_type == "unknown" or rhs_type == "unknown":
                continue
            lhs_rank = graph.essential_type_rank(lhs_type)
            rhs_rank = graph.essential_type_rank(rhs_type)
            if rhs_rank > lhs_rank:
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"Assignment from essential type '{rhs_type}' to narrower "
                            f"essential type '{lhs_type}'."
                        ),
                        risk_description="Value truncation or wrap-around may occur without diagnostic.",
                        confidence_factors={
                            "ast_match_specificity": 0.92,
                            "type_information_complete": 0.88,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.75,
                        },
                        confidence_score=0.9,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code=f"cast expression to {lhs_type} explicitly",
                            rationale="Use an explicit cast to document intentional narrowing.",
                            confidence_score=0.75,
                        ),
                    )
                )

        for node in graph.nodes_by_kind("VarDecl"):
            init_children = [
                child
                for child in graph.children(node["node_id"])
                if child.get("node_kind") not in {"BuiltinType", "RecordType", "PointerType"}
            ]
            if not init_children:
                continue
            lhs_type = node.get("essential_type", "unknown")
            rhs_type = init_children[0].get("essential_type", "unknown")
            if lhs_type == "unknown" or rhs_type == "unknown":
                continue
            if graph.essential_type_rank(rhs_type) > graph.essential_type_rank(lhs_type):
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"Initializer of essential type '{rhs_type}' assigned to narrower "
                            f"essential type '{lhs_type}'."
                        ),
                        risk_description="Initializer narrowing may truncate constant values.",
                        confidence_factors={
                            "ast_match_specificity": 0.88,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.12,
                            "fix_generator_certainty": 0.7,
                        },
                        confidence_score=0.86,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code=f"cast initializer to {lhs_type}",
                            rationale="Document intentional narrowing at initialization.",
                            confidence_score=0.7,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t value = (uint16_t)0xFFFFU;"],
            non_compliant=["uint8_t narrow = 0xFFFFU;"],
        )
