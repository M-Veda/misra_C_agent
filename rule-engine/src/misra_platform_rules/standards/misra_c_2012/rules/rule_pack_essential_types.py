"""Essential Types rule pack (Phase 3) — additional MISRA C:2012 Rule 10.x
detectors that reuse `EssentialTypeAnalyzer`. Rules 10.1 and 10.3 ship as
individual files (`rule_10_1.py`, `rule_10_3.py`) from Phase 1.2/1.3; this
pack file adds Rule 10.2."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_ARITHMETIC_OPCODES = {"+", "-"}


class Rule10_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-2",
            rule_number="10.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Character-typed expressions shall not be used inappropriately in +/-",
            description=(
                "Expressions of essentially character type shall not be used "
                "inappropriately in addition and subtraction operations."
            ),
            rationale=(
                "Mixing character and non-character essential types in arithmetic hides "
                "intent and risks locale/encoding-dependent behaviour."
            ),
            tags=["essential-types", "character-arithmetic"],
            references=["MISRA C:2012 Rule 10.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_essential_types",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.ESSENTIAL_TYPES,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        essential_types = self.essential_types()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            if opcode not in _ARITHMETIC_OPCODES:
                continue
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            left_type = essential_types.essential_type_of(children[0])
            right_type = essential_types.essential_type_of(children[1])
            is_char_pair = left_type == "char" and right_type == "char"
            involves_char = left_type == "char" or right_type == "char"
            if not involves_char or is_char_pair:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Character-typed operand combined with essential type "
                        f"'{right_type if left_type == 'char' else left_type}' via '{opcode}'."
                    ),
                    risk_description="Character arithmetic mixed with non-character types is often unintended.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.92,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.55,
                    },
                    confidence_score=0.8,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="cast the character operand explicitly before the arithmetic operation",
                        rationale="Make the intended numeric interpretation of the character explicit.",
                        confidence_score=0.55,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["char a = 'b';\nchar b = 'a';\nint16_t diff = (int16_t)(a - b);"],
            non_compliant=["char c = 'A';\nuint16_t total = c + count;"],
        )
