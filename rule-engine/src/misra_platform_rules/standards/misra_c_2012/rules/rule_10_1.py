"""MISRA C:2012 Rule 10.1 — operands shall not be of an inappropriate essential type."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix

_INAPPROPRIATE_PAIRS = {
    ("boolean", "signed_char"),
    ("boolean", "unsigned_char"),
    ("boolean", "signed_short"),
    ("boolean", "unsigned_short"),
    ("boolean", "signed_int"),
    ("boolean", "unsigned_int"),
    ("boolean", "signed_long"),
    ("boolean", "unsigned_long"),
    ("boolean", "float"),
    ("boolean", "double"),
    ("signed_char", "unsigned_char"),
    ("signed_short", "unsigned_short"),
    ("signed_int", "unsigned_int"),
    ("signed_long", "unsigned_long"),
    ("signed_long_long", "unsigned_long_long"),
}


class Rule10_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-1",
            rule_number="10.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Operands shall not be of an inappropriate essential type",
            description="Operands of operators shall not use essential types in inappropriate combinations.",
            rationale="Essential type category mismatches are a common source of embedded defects.",
            tags=["essential-types", "operators"],
            references=["MISRA C:2012 Rule 10.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_10_1",
            requires_ast_nodes=["BinaryOperator"],
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            left_type = children[0].get("essential_type", "unknown")
            right_type = children[1].get("essential_type", "unknown")
            if left_type == "unknown" or right_type == "unknown":
                continue
            pair = (left_type, right_type)
            reverse_pair = (right_type, left_type)
            if pair not in _INAPPROPRIATE_PAIRS and reverse_pair not in _INAPPROPRIATE_PAIRS:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Binary operation combines essential types '{left_type}' and "
                        f"'{right_type}' in an inappropriate category pairing."
                    ),
                    risk_description=(
                        "Implicit conversions between essential categories may change value semantics."
                    ),
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.7,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="cast operands to a common essential type category",
                        rationale="Normalize operand essential types before evaluation.",
                        confidence_score=0.7,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t a = 1U;\nuint16_t b = 2U;\nuint16_t c = a + b;"],
            non_compliant=["bool flag = true;\nuint16_t value = flag + 1U;"],
        )
