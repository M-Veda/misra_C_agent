"""MISRA C:2012 Rule 11.8 — pointer cast shall not remove const/volatile qualification."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


class Rule11_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-8",
            rule_number="11.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Pointer cast shall not remove const or volatile qualification",
            description=(
                "A cast shall not remove any const or volatile qualification from the type "
                "addressed by a pointer."
            ),
            rationale="Removing qualifiers enables modification of read-only or volatile data.",
            tags=["pointers", "casts", "qualifiers"],
            references=["MISRA C:2012 Rule 11.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_11_8",
            requires_ast_nodes=["CStyleCastExpr", "ImplicitCastExpr"],
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("CStyleCastExpr", "ImplicitCastExpr"):
            for node in graph.nodes_by_kind(kind):
                props = node.get("semantic_properties", {})
                if not props.get("removes_qualifier", False):
                    continue
                removed = props.get("removed_qualifiers", [])
                if not removed:
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"Cast removes qualifier(s) {removed} from the addressed type."
                        ),
                        risk_description="Qualified data may be modified through an unqualified pointer.",
                        confidence_factors={
                            "ast_match_specificity": 0.95,
                            "type_information_complete": 0.9,
                            "macro_clarity": 0.92,
                            "historical_false_positive_rate": 0.08,
                            "fix_generator_certainty": 0.65,
                        },
                        confidence_score=0.91,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="preserve const/volatile in target pointer type",
                            rationale="Avoid casts that strip type qualifiers from pointed-to types.",
                            confidence_score=0.65,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["const uint8_t *cp = buffer;\n(void)cp;"],
            non_compliant=["uint8_t *p = (uint8_t *)const_buffer;"],
        )
