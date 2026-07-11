"""Conversions rule pack (Phase 3/5) — MISRA C:2012 Rules 10.4, 10.5, 10.7,
7.4, 11.1, 11.6.

All detectors reuse `EssentialTypeAnalyzer`/`CastAnalyzer`/`QualifierAnalyzer`/
`PointerAnalyzer` rather than re-deriving essential-type-category or pointer
comparisons inline.
"""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_ARITHMETIC_OPCODES = {"+", "-", "*", "/", "%"}


class Rule10_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-4",
            rule_number="10.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Operands of an arithmetic operator shall have the same essential type category",
            description=(
                "Both operands of an operator in which the usual arithmetic conversions are "
                "performed shall have the same essential type category."
            ),
            rationale="Cross-category arithmetic conversions can silently change value semantics.",
            tags=["essential-types", "conversions"],
            references=["MISRA C:2012 Rule 10.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
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
            left = essential_types.essential_type_of(children[0])
            right = essential_types.essential_type_of(children[1])
            if left == "unknown" or right == "unknown":
                continue
            left_category = essential_types.category(left)
            right_category = essential_types.category(right)
            if left_category == right_category:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Operator '{opcode}' combines essential type categories "
                        f"'{left_category}' and '{right_category}'."
                    ),
                    risk_description="Usual arithmetic conversions across categories can lose sign/precision.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.6,
                    },
                    confidence_score=0.83,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="cast one operand to match the other's essential type category",
                        rationale="Make the intended common essential type explicit.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int16_t a = 1;\nint16_t b = 2;\nint16_t c = a + b;"],
            non_compliant=["int16_t a = 1;\nfloat32_t b = 2.0f;\nfloat32_t c = a + b;"],
        )


class Rule10_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-5",
            rule_number="10.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A cast should not change the essential type category of an expression",
            description="A cast should not be used to change the essential type category of an expression.",
            rationale="Category-changing casts often mask a design error rather than express intent.",
            tags=["essential-types", "casts"],
            references=["MISRA C:2012 Rule 10.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        essential_types = self.essential_types()
        casts = self.casts()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            if not casts.is_explicit_cast(node):
                continue
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            target = essential_types.essential_type_of(node)
            source = essential_types.essential_type_of(operand)
            if target == "unknown" or source == "unknown":
                continue
            if essential_types.category(target) == essential_types.category(source):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Cast changes essential type category from '{essential_types.category(source)}' "
                        f"to '{essential_types.category(target)}'."
                    ),
                    risk_description="Category-changing casts frequently indicate an underlying design issue.",
                    confidence_factors={
                        "ast_match_specificity": 0.8,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.72,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="reconsider whether a category-changing cast is truly intended",
                        rationale="Review the design rationale for crossing essential type categories.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int16_t a = 1;\nint32_t b = (int32_t)a;"],
            non_compliant=["int16_t a = 1;\nfloat32_t b = (float32_t)a;"],
        )


class Rule10_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-7",
            rule_number="10.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A composite expression's cast essential type shall match the other operand's category",
            description=(
                "If a composite expression is used as one operand of an operator, and the "
                "other operand has a different essential type category, an explicit cast on "
                "the composite operand shall not introduce a further category mismatch."
            ),
            rationale="Casting one side of a mixed-category operation to a third category compounds ambiguity.",
            tags=["essential-types", "conversions", "composite-expressions"],
            references=["MISRA C:2012 Rule 10.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["BinaryOperator", "CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        essential_types = self.essential_types()
        casts = self.casts()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            for cast_side, other_side in ((children[0], children[1]), (children[1], children[0])):
                if not casts.is_cast(cast_side):
                    continue
                cast_operand_children = graph.children(cast_side["node_id"])
                if not cast_operand_children or cast_operand_children[0].get("node_kind") not in (
                    "BinaryOperator",
                    "UnaryOperator",
                ):
                    continue  # only flag casts applied to a *composite* (sub-)expression
                cast_target = essential_types.essential_type_of(cast_side)
                other_type = essential_types.essential_type_of(other_side)
                if cast_target == "unknown" or other_type == "unknown":
                    continue
                if essential_types.category(cast_target) == essential_types.category(other_type):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"Composite expression cast to essential category "
                            f"'{essential_types.category(cast_target)}' is combined with an operand of "
                            f"category '{essential_types.category(other_type)}'."
                        ),
                        risk_description="Nested category mismatches on composite expressions are error-prone.",
                        confidence_factors={
                            "ast_match_specificity": 0.78,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.25,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.7,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="align the composite expression's cast target with the other operand's category",
                            rationale="Reduce ambiguity in mixed-category composite expressions.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t total = (int32_t)(a + b) + c;  /* all int category */"],
            non_compliant=["float32_t total = (float32_t)(a + b) + flag;  /* flag is boolean */"],
        )


class Rule7_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-7-4",
            rule_number="7.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A string literal shall not be assigned to an object unless the object's type is pointer to const-qualified char",
            description="A string literal shall only be assigned/initialized to a pointer-to-const-qualified-char object.",
            rationale="String literals have a read-only, indeterminate storage duration; writing through them is undefined behaviour.",
            tags=["conversions", "qualifiers", "strings"],
            references=["MISRA C:2012 Rule 7.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["VarDecl", "StringLiteral"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        qualifiers = self.qualifiers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("VarDecl"):
            init_children = [
                child
                for child in graph.children(node["node_id"])
                if child.get("node_kind") not in {"BuiltinType", "RecordType", "PointerType"}
            ]
            if not init_children or init_children[0].get("node_kind") != "StringLiteral":
                continue
            if qualifiers.is_const(node):
                continue
            name = node.get("semantic_properties", {}).get("name", "<unnamed>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"String literal assigned to '{name}', which is not pointer-to-const-qualified char.",
                    risk_description="Writing through a pointer to a string literal is undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.7,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=f"char *{name} = ...;",
                        suggested_code=f"const char *{name} = ...;",
                        rationale="Qualify the pointer as const when it points to a string literal.",
                        confidence_score=0.7,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["const char *greeting = \"hello\";"],
            non_compliant=["char *greeting = \"hello\"; /* missing const */"],
        )


class Rule11_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-1",
            rule_number="11.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Conversions shall not be performed between a pointer to a function and any other type",
            description=(
                "A cast shall not convert a function pointer to a non-function-pointer type, or "
                "vice versa, or to an incompatible function pointer type."
            ),
            rationale="Function-pointer conversions are not portable and can produce a pointer that is unsafe to call.",
            tags=["conversions", "pointers", "functions"],
            references=["MISRA C:2012 Rule 11.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        casts = self.casts()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            target_spelling = node.get("type_information", {}).get("spelling", "")
            source_spelling = operand.get("type_information", {}).get("spelling", "")
            target_is_function_pointer = "(" in target_spelling
            source_is_function_pointer = "(" in source_spelling
            violates = casts.is_function_pointer_cast(node, operand) or (
                target_is_function_pointer != source_is_function_pointer
                and (target_is_function_pointer or source_is_function_pointer)
            )
            if not violates:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Cast converts between a function pointer and an incompatible type.",
                    risk_description="Calling through a function pointer converted from an incompatible type is undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.25,
                    },
                    confidence_score=0.78,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void (*handler)(int32_t) = &on_tick;"],
            non_compliant=["void (*handler)(int32_t) = (void (*)(int32_t))some_data_pointer;"],
        )


class Rule11_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-6",
            rule_number="11.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A cast shall not be performed between pointer to void and an arithmetic type",
            description="A cast shall not convert pointer-to-void into an arithmetic type, or vice versa.",
            rationale="void*/arithmetic conversions discard the type information the compiler could otherwise check.",
            tags=["conversions", "pointers"],
            references=["MISRA C:2012 Rule 11.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            node_is_void_ptr = pointers.is_pointer(node) and pointers.pointee_type(node) in ("void", "const void")
            operand_is_void_ptr = pointers.is_pointer(operand) and pointers.pointee_type(operand) in (
                "void",
                "const void",
            )
            node_is_arithmetic = not pointers.is_pointer(node) and node.get("essential_type", "unknown") not in (
                "unknown",
                "void",
            )
            operand_is_arithmetic = not pointers.is_pointer(
                operand
            ) and operand.get("essential_type", "unknown") not in ("unknown", "void")

            if not ((node_is_void_ptr and operand_is_arithmetic) or (operand_is_void_ptr and node_is_arithmetic)):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Cast converts between pointer-to-void and an arithmetic type.",
                    risk_description="void*/arithmetic conversions bypass type checking on the value's true representation.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.82,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.78,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t *p = create_buffer(); /* stays a pointer */"],
            non_compliant=["void *raw = create_buffer();\nuint32_t address = (uint32_t)raw; /* void* to arithmetic */"],
        )


class Rule10_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-6",
            rule_number="10.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A composite expression shall not be assigned to a wider essential type",
            description=(
                "The value of a composite expression shall not be assigned to an object "
                "with a wider essential type."
            ),
            rationale="Widening a composite expression's result can hide intermediate truncation.",
            tags=["essential-types", "conversions", "composite-expressions"],
            references=["MISRA C:2012 Rule 10.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        essential_types = self.essential_types()
        casts = self.casts()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            if node.get("semantic_properties", {}).get("opcode") != "=":
                continue
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            lhs, rhs = children[0], children[1]
            if not casts.is_composite_expression(rhs):
                continue
            lhs_type = essential_types.essential_type_of(lhs)
            rhs_type = essential_types.essential_type_of(rhs)
            if lhs_type == "unknown" or rhs_type == "unknown":
                continue
            if not essential_types.is_wider(lhs_type, rhs_type):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Composite expression of essential type '{rhs_type}' assigned to "
                        f"wider essential type '{lhs_type}'."
                    ),
                    risk_description="Widening a composite expression can hide intermediate truncation.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.12,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="assign to a temporary of the composite expression's essential type first",
                        rationale="Avoid widening the result of a composite expression directly.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t narrow = (uint16_t)(a + b);"],
            non_compliant=["uint32_t wide = (uint16_t)a + (uint16_t)b; /* composite to wider */"],
        )


class Rule10_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-10-8",
            rule_number="10.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A composite expression cast to a wider category shall not be used as an operand",
            description=(
                "A composite expression shall not be cast to a different, wider essential "
                "type category before being used as an operand."
            ),
            rationale="Category-widening casts on composite expressions compound conversion ambiguity.",
            tags=["essential-types", "conversions", "composite-expressions", "casts"],
            references=["MISRA C:2012 Rule 10.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_conversions",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.CONVERSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        casts = self.casts()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            if not casts.is_composite_expression(operand):
                continue
            if not casts.changes_to_wider_category(node, operand):
                continue
            parent = graph.get(node.get("parent_id", ""))
            if not parent or parent.get("node_kind") not in (
                "BinaryOperator",
                "UnaryOperator",
                "CallExpr",
                "ArraySubscriptExpr",
            ):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A composite expression is cast to a wider essential type category before use.",
                    risk_description="Category-widening casts on composite expressions are error-prone.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.82,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.82,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="evaluate the composite expression without widening its category",
                        rationale="Keep composite-expression essential types consistent with operands.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t total = (int32_t)(a + b);"],
            non_compliant=["float32_t total = (float32_t)(a + b) + c; /* composite cast to wider category */"],
        )
