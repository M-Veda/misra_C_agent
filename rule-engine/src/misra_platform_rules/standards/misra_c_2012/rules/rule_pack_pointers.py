"""Pointers rule pack (Phase 3/5) — MISRA C:2012 Rules 11.4, 11.5, 11.9,
18.2, 18.3, 18.4, 19.1. Rule 11.8 ships separately (`rule_11_8.py`). Rule
19.1 (Phase 5) reuses `AliasAnalyzer` for a genuinely sound overlap signal
rather than a syntactic name comparison."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


class Rule11_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-4",
            rule_number="11.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A conversion should not be performed between a pointer and an integer type",
            description="A cast should not convert a pointer type to an integer type, or vice versa.",
            rationale="Pointer/integer casts are non-portable and hide the true type of an address.",
            tags=["pointers", "casts"],
            references=["MISRA C:2012 Rule 11.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.POINTERS,
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
            target_is_pointer = pointers.is_pointer(node)
            source_is_pointer = pointers.is_pointer(operand)
            target_is_integer = node.get("type_information", {}).get("is_integer", False)
            source_is_integer = operand.get("type_information", {}).get("is_integer", False)
            if not ((target_is_pointer and source_is_integer) or (source_is_pointer and target_is_integer)):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Cast converts between a pointer type and an integer type.",
                    risk_description="Pointer/integer representation is platform-dependent and unsafe to assume.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.88,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.35,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="avoid converting between pointer and integer types",
                        rationale="Use uintptr_t only where a documented platform contract requires it.",
                        confidence_score=0.35,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t *p = &buffer[0];"],
            non_compliant=["uint32_t address = (uint32_t)&buffer[0];"],
        )


class Rule11_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-5",
            rule_number="11.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A conversion from pointer-to-void into pointer-to-object should not be performed",
            description="A conversion should not be performed from a pointer to void into a pointer to an object type.",
            rationale="void* conversions bypass type checking that would otherwise catch object-type mismatches.",
            tags=["pointers", "casts"],
            references=["MISRA C:2012 Rule 11.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["CStyleCastExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.POINTERS,
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
            if not pointers.is_pointer(node) or not pointers.is_pointer(operand):
                continue
            source_pointee = pointers.pointee_type(operand)
            target_pointee = pointers.pointee_type(node)
            if source_pointee not in ("void", "const void"):
                continue
            if target_pointee in ("void", "const void", ""):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Cast converts a void pointer into pointer-to-'{target_pointee}'.",
                    risk_description="The compiler cannot verify the object actually has the target type.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.72,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="pass/store a correctly-typed pointer instead of converting through void*",
                        rationale="Avoid implicit trust in a void* payload's real type.",
                        confidence_score=0.3,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["sensor_t *sensor = create_sensor();"],
            non_compliant=["void *raw = create_sensor();\nsensor_t *sensor = (sensor_t *)raw;"],
        )


class Rule11_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-11-9",
            rule_number="11.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="NULL shall be the only integer constant used to represent a null pointer",
            description="The macro NULL shall be the only integer null-pointer-constant used.",
            rationale="Bare 0 casts obscure the null-pointer intent and cannot be searched for consistently.",
            tags=["pointers", "null-pointer"],
            references=["MISRA C:2012 Rule 11.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["CStyleCastExpr", "IntegerLiteral"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.POINTERS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            if not pointers.is_pointer(node):
                continue
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            if not pointers.is_null_constant(operand):
                continue
            macro_name = operand.get("macro_origin", {}).get("macro_name", "")
            if macro_name == "NULL":
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A bare integer 0 (not the NULL macro) is cast to a pointer type.",
                    risk_description="Inconsistent null-pointer spellings hide intent and complicate review.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.7,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.8,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="NULL",
                        rationale="Use the NULL macro to spell the null-pointer constant.",
                        confidence_score=0.8,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t *p = NULL;"],
            non_compliant=["uint8_t *p = (uint8_t *)0;"],
        )


class Rule18_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-18-2",
            rule_number="18.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Subtraction between pointers shall only be applied to elements of the same array",
            description="Subtraction shall not be applied to two pointers that do not point into the same array.",
            rationale="Subtracting pointers into different objects is undefined behaviour.",
            tags=["pointers", "arrays"],
            references=["MISRA C:2012 Rule 18.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.POINTERS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            if not pointers.is_two_pointer_subtraction(node, children):
                continue
            left_pointee = pointers.pointee_type(children[0])
            right_pointee = pointers.pointee_type(children[1])
            if not left_pointee or not right_pointee or left_pointee == right_pointee:
                # Same pointee type is necessary but not sufficient for "same array";
                # flagging only the definite mismatch case avoids false positives.
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Pointer subtraction between incompatible pointee types "
                        f"'{left_pointee}' and '{right_pointee}'."
                    ),
                    risk_description="Pointers into different arrays/objects cannot be validly subtracted.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.88,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.86,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["ptrdiff_t n = &array[5] - &array[0];"],
            non_compliant=["ptrdiff_t n = &array_a[0] - &array_b[0];"],
        )


class Rule18_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-18-3",
            rule_number="18.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Relational operators shall only be applied to pointers into the same object",
            description="<, >, <=, >= shall not compare pointers that do not point into the same array/object.",
            rationale="Relational comparison of pointers into different objects is undefined behaviour.",
            tags=["pointers", "arrays"],
            references=["MISRA C:2012 Rule 18.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.POINTERS,
            requires_type_info=True,
        )

    _RELATIONAL_OPCODES = {"<", ">", "<=", ">="}

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            if opcode not in self._RELATIONAL_OPCODES:
                continue
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            left, right = children[0], children[1]
            if not (pointers.is_pointer(left) and pointers.is_pointer(right)):
                continue
            left_pointee = pointers.pointee_type(left)
            right_pointee = pointers.pointee_type(right)
            if not left_pointee or not right_pointee or left_pointee == right_pointee:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Relational operator '{opcode}' compares pointers with incompatible "
                        f"pointee types '{left_pointee}' and '{right_pointee}'."
                    ),
                    risk_description="Comparing pointers into different objects with <, >, <=, >= is undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.12,
                        "fix_generator_certainty": 0.25,
                    },
                    confidence_score=0.83,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["bool_t before = (&array[i] < &array[j]);"],
            non_compliant=["bool_t before = (&array_a[0] < &array_b[0]); /* different objects */"],
        )


class Rule18_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-18-4",
            rule_number="18.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The +, -, += and -= operators should not be applied to an expression of pointer type",
            description="Pointer arithmetic via +, -, += or -= should be avoided in favour of array indexing.",
            rationale="Direct pointer arithmetic is harder to bound-check by inspection than array indexing.",
            tags=["pointers", "arithmetic"],
            references=["MISRA C:2012 Rule 18.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.POINTERS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            children = graph.children(node["node_id"])
            if not pointers.is_pointer_arithmetic(node, children):
                continue
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Pointer arithmetic performed using the '{opcode}' operator.",
                    risk_description="Pointer arithmetic is harder to bound-check by inspection than array indexing.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.7,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="index the array instead of performing pointer arithmetic directly",
                        rationale="Array indexing documents bounds more clearly than raw pointer arithmetic.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t value = buffer[index];"],
            non_compliant=["uint8_t value = *(buffer + index); /* pointer arithmetic */"],
        )


class Rule19_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-19-1",
            rule_number="19.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="An object shall not be copied to an overlapping object",
            description="memcpy (and similar copies) shall not be used on source/destination pointers that may alias.",
            rationale="memcpy's behaviour on overlapping regions is undefined; memmove exists precisely for that case.",
            tags=["pointers", "aliasing", "memory"],
            references=["MISRA C:2012 Rule 19.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_pointers",
            requires_ast_nodes=["CallExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.POINTERS,
            requires_dataflow=True,
        )

    _OVERLAP_SENSITIVE_CALLEES = {"memcpy", "strcpy", "strcat"}

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            if not any(
                child.get("node_kind") == "CompoundStmt" for child in graph.children(function_node["node_id"])
            ):
                continue
            aliases = self.aliases(function_node, graph, context)
            for call_node in graph.descendants(function_node["node_id"]):
                if call_node.get("node_kind") != "CallExpr":
                    continue
                callee = call_node.get("semantic_properties", {}).get("callee", "")
                if callee not in self._OVERLAP_SENSITIVE_CALLEES:
                    continue
                args = graph.children(call_node["node_id"])
                if len(args) < 2:
                    continue
                dest, source = args[0], args[1]
                if dest.get("node_kind") != "DeclRefExpr" or source.get("node_kind") != "DeclRefExpr":
                    continue
                dest_name = dest.get("semantic_properties", {}).get("name", "")
                source_name = source.get("semantic_properties", {}).get("name", "")
                if not dest_name or not source_name or dest_name == source_name:
                    continue
                may_alias, confidence = aliases.may_alias(dest_name, source_name)
                if not may_alias:
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        call_node,
                        explanation=(
                            f"'{callee}({dest_name}, {source_name}, ...)' may copy between overlapping "
                            f"objects ({confidence} alias)."
                        ),
                        risk_description=f"{callee}'s behaviour on overlapping source/destination is undefined.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.7,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.2,
                            "fix_generator_certainty": 0.5,
                        },
                        confidence_score=0.9 if confidence == "definite" else 0.65,
                        suggested_fix=SuggestedFix(
                            original_code=f"{callee}({dest_name}, {source_name}, n)",
                            suggested_code=f"memmove({dest_name}, {source_name}, n)",
                            rationale="Use memmove when source and destination may overlap.",
                            confidence_score=0.5,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t *p = &buffer[0];\nuint8_t *q = &other_buffer[0];\nmemcpy(p, q, n);"],
            non_compliant=[
                "uint8_t *p = &buffer[0];\nuint8_t *q = &buffer[0]; /* aliases p */\nmemcpy(p, q, n);"
            ],
        )
