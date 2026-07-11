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


def _meta_true(value: object) -> bool:
    return value is True or value == "true"


_INT_BIT_FIELD_CATEGORIES = frozenset({"signed_int", "unsigned_int"})


class Rule6_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-6-1",
            rule_number="6.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Bit-fields shall only be declared as explicit unsigned or signed int",
            description="A bit-field shall have type signed int or unsigned int only.",
            rationale="Other bit-field base types have implementation-defined behaviour.",
            tags=["essential-types", "bit-fields"],
            references=["MISRA C:2012 Rule 6.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_essential_types",
            requires_ast_nodes=["FieldDecl"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.ESSENTIAL_TYPES,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("FieldDecl"):
            props = node.get("semantic_properties", {})
            if _meta_true(props.get("invalid_bit_field_type")):
                name = props.get("name", "<field>")
                results.append(self._result(context, graph, node, name, "invalid bit-field base type"))
                continue
            if not _meta_true(props.get("is_bit_field")):
                continue
            category = props.get("bit_field_type_category", "")
            if category in _INT_BIT_FIELD_CATEGORIES:
                continue
            name = props.get("name", "<field>")
            results.append(
                self._result(
                    context,
                    graph,
                    node,
                    name,
                    f"bit-field base category '{category}' is not signed/unsigned int",
                )
            )
        return results

    def _result(
        self, context: RuleContext, graph: AstGraph, node: dict, name: str, detail: str
    ) -> RuleResult:
        return self.make_result(
            context,
            graph,
            node,
            explanation=f"Bit-field '{name}' has {detail}.",
            risk_description="Only signed int and unsigned int bit-fields are permitted.",
            confidence_factors={
                "ast_match_specificity": 0.92,
                "type_information_complete": 0.88,
                "macro_clarity": 0.95,
                "historical_false_positive_rate": 0.08,
                "fix_generator_certainty": 0.55,
            },
            confidence_score=0.88,
            suggested_fix=SuggestedFix(
                original_code=AstGraph.offending_text(node),
                suggested_code=f"declare '{name}' as a signed int or unsigned int bit-field",
                rationale="Restrict bit-fields to explicit signed/unsigned int types.",
                confidence_score=0.55,
            ),
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct flags_tag {\n    unsigned int ready : 1;\n};"],
            non_compliant=["struct flags_tag {\n    uint8_t ready : 1;\n};"],
        )


class Rule6_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-6-2",
            rule_number="6.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Single-bit named bit-fields shall not be of a signed type",
            description="A named bit-field of width 1 shall not have signed type.",
            rationale="Single-bit signed bit-fields have implementation-defined representation.",
            tags=["essential-types", "bit-fields"],
            references=["MISRA C:2012 Rule 6.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_essential_types",
            requires_ast_nodes=["FieldDecl"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.ESSENTIAL_TYPES,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("FieldDecl"):
            props = node.get("semantic_properties", {})
            width = props.get("bit_field_width")
            if width != 1 and width != "1":
                continue
            if not _meta_true(props.get("bit_field_is_signed")):
                continue
            name = props.get("name", "<field>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Single-bit bit-field '{name}' is declared with signed type.",
                    risk_description="Single-bit signed bit-fields are implementation-defined.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.6,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code=f"declare '{name}' as unsigned int : 1",
                        rationale="Use unsigned int for single-bit bit-fields.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct flags_tag {\n    unsigned int ready : 1;\n};"],
            non_compliant=["struct flags_tag {\n    signed int ready : 1;\n};"],
        )
