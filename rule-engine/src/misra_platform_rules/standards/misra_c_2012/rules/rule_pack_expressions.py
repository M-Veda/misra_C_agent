"""Expressions rule pack (Phase 3/5) — MISRA C:2012 Rules 12.3, 13.4, 13.5,
14.4, 13.1, 13.6. All reuse `ExpressionClassifier`."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_LOGICAL_OPCODES = {"&&", "||"}


class Rule12_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-12-3",
            rule_number="12.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The comma operator should not be used",
            description="The comma operator should not be used.",
            rationale="Comma-operator expressions bury a statement's side effects inside an expression.",
            tags=["expressions"],
            references=["MISRA C:2012 Rule 12.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("BinaryOperator"):
            if not classifier.uses_comma_operator(node):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="The comma operator is used to sequence expressions.",
                    risk_description="Comma-operator side effects are easy to overlook during review.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.55,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="split into separate statements",
                        rationale="Make each side effect an explicit, separate statement.",
                        confidence_score=0.55,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["i++;\nj = i;"],
            non_compliant=["j = (i++, i);"],
        )


class Rule13_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-4",
            rule_number="13.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The result of an assignment operator should not be used",
            description="The result of an assignment expression should not itself be used as a value.",
            rationale="Using an assignment's result mixes side effect and evaluation, hurting readability.",
            tags=["expressions", "side-effects"],
            references=["MISRA C:2012 Rule 13.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    _ASSIGNMENT_OPCODES = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("BinaryOperator"):
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            if opcode not in self._ASSIGNMENT_OPCODES:
                continue
            parent = graph.get(node.get("parent_id", ""))
            if not parent or parent.get("node_kind") == "CompoundStmt":
                continue  # used as a standalone statement: compliant
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"The result of assignment ('{opcode}') is used inside a '{parent.get('node_kind')}'.",
                    risk_description="Assignment-as-value obscures whether the code intended comparison or assignment.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.78,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="perform the assignment as its own statement before use",
                        rationale="Separate the side effect from the value it produces.",
                        confidence_score=0.45,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["x = read_value();\nif (x == 0) {\n    /* ... */\n}"],
            non_compliant=["if ((x = read_value()) == 0) {\n    /* ... */\n}"],
        )


class Rule13_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-5",
            rule_number="13.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The right-hand operand of && or || shall not contain persistent side effects",
            description="Because short-circuit evaluation may skip it, the RHS of && / || shall have no side effects.",
            rationale="Short-circuit evaluation means the RHS's side effect may or may not run.",
            tags=["expressions", "side-effects"],
            references=["MISRA C:2012 Rule 13.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("BinaryOperator"):
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            if opcode not in _LOGICAL_OPCODES:
                continue
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            rhs = children[1]
            if not classifier.has_side_effects(rhs, graph):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Right-hand operand of '{opcode}' has a persistent side effect.",
                    risk_description="Short-circuiting may silently skip the side effect at runtime.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.8,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="move the side-effecting expression to its own statement before the condition",
                        rationale="Do not rely on short-circuit evaluation to run a side effect.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["ready = poll_sensor();\nif (armed && ready) {\n    /* ... */\n}"],
            non_compliant=["if (armed && poll_sensor()) {\n    /* ... */\n}"],
        )


class Rule14_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-14-4",
            rule_number="14.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The controlling expression of an if/iteration statement shall be essentially Boolean",
            description="The controlling expression of if/while/for/do shall have essentially Boolean type.",
            rationale="Non-Boolean controlling expressions (e.g. bare pointers/integers) hide the true test.",
            tags=["expressions", "control-flow", "essential-types"],
            references=["MISRA C:2012 Rule 14.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["IfStmt", "WhileStmt", "ForStmt", "DoStmt"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.EXPRESSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.all_nodes():
            if not classifier.is_essentially_boolean_context_mismatch(node, graph):
                continue
            essential_type = classifier.essential_type_of(node)
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Controlling expression has essential type '{essential_type}', not boolean."
                    ),
                    risk_description="Implicit truthiness tests hide the actual condition being checked.",
                    confidence_factors={
                        "ast_match_specificity": 0.8,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="compare explicitly, e.g. (x != 0) instead of (x)",
                        rationale="Make the Boolean test explicit rather than relying on implicit conversion.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["if (count != 0U) {\n    /* ... */\n}"],
            non_compliant=["if (count) {\n    /* ... */\n}"],
        )


class Rule13_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-1",
            rule_number="13.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Initializer lists shall not contain persistent side effects",
            description="No element of an initializer list shall itself have a persistent side effect.",
            rationale="Initializer evaluation order is unspecified, so side effects there are unpredictable.",
            tags=["expressions", "initialization", "side-effects"],
            references=["MISRA C:2012 Rule 13.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["InitListExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("InitListExpr"):
            for element in graph.children(node["node_id"]):
                if not classifier.has_side_effects(element, graph):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        element,
                        explanation="An initializer-list element has a persistent side effect.",
                        risk_description="Initializer evaluation order is unspecified by the standard.",
                        confidence_factors={
                            "ast_match_specificity": 0.88,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.12,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.8,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(element),
                            suggested_code="compute the side-effecting value before the initializer list",
                            rationale="Move side effects out of an initializer list into their own statement.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t next = read_sensor();\nint32_t values[2] = {next, 0};"],
            non_compliant=["int32_t values[2] = {read_sensor(), 0}; /* side effect in initializer */"],
        )


class Rule13_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-6",
            rule_number="13.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="The operand of the sizeof operator shall not contain a persistent side effect",
            description="The operand of sizeof shall not have a persistent side effect.",
            rationale="sizeof's operand is not evaluated (except VLAs), so any side effect never actually runs.",
            tags=["expressions", "side-effects", "sizeof"],
            references=["MISRA C:2012 Rule 13.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["UnaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("UnaryOperator"):
            if node.get("semantic_properties", {}).get("opcode") != "sizeof":
                continue
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            if not classifier.has_side_effects(operand, graph):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="The operand of 'sizeof' has a persistent side effect that will never run.",
                    risk_description="sizeof's operand is not evaluated, so the intended side effect silently never happens.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.08,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use a type name or a side-effect-free expression inside sizeof",
                        rationale="Do not rely on sizeof to evaluate its operand.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["size_t n = sizeof(buffer);"],
            non_compliant=["size_t n = sizeof(buffer[index++]); /* index++ never actually runs */"],
        )


class Rule13_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-3",
            rule_number="13.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A full expression containing ++/-- should have no other potential side effect",
            description="A full expression that contains an increment or decrement should not also have other side effects.",
            rationale="Mixing ++/-- with other side effects in one expression obscures evaluation order.",
            tags=["expressions", "side-effects"],
            references=["MISRA C:2012 Rule 13.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["UnaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("UnaryOperator"):
            if not classifier.is_increment_or_decrement(node):
                continue
            if not classifier.has_other_side_effects_in_full_expression(node, graph):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A full expression containing ++/-- also has another side effect.",
                    risk_description="Multiple side effects in one expression are hard to reason about.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.78,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="split the increment/decrement into its own statement",
                        rationale="Keep ++/-- as the only side effect in its full expression.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["++index;"],
            non_compliant=["array[index++] = value; /* assignment and increment */"],
        )


class Rule17_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-7",
            rule_number="17.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The value returned by a non-void function shall be used or cast to void",
            description="A call to a function with non-void return type shall not discard its result.",
            rationale="Ignoring a return value often means an error indication was dropped on the floor.",
            tags=["expressions", "functions"],
            references=["MISRA C:2012 Rule 17.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            if not classifier.is_discarded_non_void_call(node, graph):
                continue
            callee = node.get("semantic_properties", {}).get("callee", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"The return value of '{callee}' is discarded.",
                    risk_description="Ignoring a non-void return may drop an error indication.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="assign the result, test it, or (void)cast explicitly",
                        rationale="Make intentional discards explicit with a (void) cast.",
                        confidence_score=0.45,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["(void)refresh_cache();"],
            non_compliant=["refresh_cache(); /* non-void result discarded */"],
        )


class Rule12_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-12-2",
            rule_number="12.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The right-hand operand of a shift operator shall lie in the range zero to one less than the width",
            description="The right-hand operand of << or >> shall be in [0, width-1].",
            rationale="Shifting by an out-of-range amount is undefined behaviour.",
            tags=["expressions", "shifts", "essential-types"],
            references=["MISRA C:2012 Rule 12.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.EXPRESSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            if not classifier.shift_amount_out_of_range(node):
                continue
            props = node.get("semantic_properties", {})
            opcode = props.get("opcode", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=(
                        f"Shift amount {props.get('shift_amount')} for '{opcode}' is outside "
                        f"[0, {props.get('shift_width', 0) - 1}]."
                    ),
                    risk_description="Out-of-range shift amounts are undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.88,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.08,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="constrain the shift amount to [0, width-1]",
                        rationale="Keep shift amounts within the representable bit width.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint32_t value = data << 3U;"],
            non_compliant=["uint32_t value = data << 32U; /* shift >= width */"],
        )


class Rule12_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-12-4",
            rule_number="12.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="Evaluation of constant unsigned integer expressions should not lead to wrap-around",
            description="A constant unsigned integer expression should not wrap on evaluation.",
            rationale="Wrap-around in constant expressions can hide an incorrect literal value.",
            tags=["expressions", "essential-types", "constants"],
            references=["MISRA C:2012 Rule 12.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.EXPRESSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            if not classifier.wraps_on_constant_unsigned(node):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Constant unsigned integer expression wraps on evaluation.",
                    risk_description="Wrap-around may indicate an incorrect constant value.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.35,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use a wider essential type or a different literal",
                        rationale="Avoid wrap-around in constant unsigned expressions.",
                        confidence_score=0.35,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint32_t mask = 0xFFFF0000U;"],
            non_compliant=["uint16_t mask = 0xFFFF0000U; /* wraps on evaluation */"],
        )


class Rule1_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-1-3",
            rule_number="1.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="There shall be no occurrence of undefined or critical unspecified behaviour",
            description="The program shall not rely on undefined or critical unspecified behaviour.",
            rationale="Undefined behaviour makes program behaviour unpredictable and untestable.",
            tags=["expressions", "undefined-behaviour"],
            references=["MISRA C:2012 Rule 1.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator", "UnaryOperator", "CallExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.all_nodes():
            if not classifier.has_undefined_behaviour(node):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="This construct has undefined or critical unspecified behaviour.",
                    risk_description="Undefined behaviour cannot be relied upon in safety-critical code.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.85,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint32_t value = data << 3U;"],
            non_compliant=["uint32_t value = data << 32U; /* undefined shift */"],
        )


class Rule13_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-13-2",
            rule_number="13.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The value of an expression shall be the same under any permitted evaluation order",
            description="An expression shall not depend on unordered evaluation of its sub-expressions.",
            rationale="Unspecified evaluation order can yield different results on different executions.",
            tags=["expressions", "evaluation-order"],
            references=["MISRA C:2012 Rule 13.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        classifier = self.expressions()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            if not classifier.has_unordered_evaluation(node):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Expression value depends on unspecified evaluation order.",
                    risk_description="Permitted evaluation orders may yield different results.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.12,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.82,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="split into separate statements with a single side effect each",
                        rationale="Do not rely on evaluation order between sub-expressions.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["i++;\narray[i] = value;"],
            non_compliant=["array[i++] = value; /* unordered evaluation */"],
        )


def _meta_true(value: object) -> bool:
    return value is True or value == "true"


class Rule4_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-4-1",
            rule_number="4.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Octal and hexadecimal escape sequences shall be terminated",
            description="Every octal or hexadecimal escape sequence in a character or string literal shall be terminated.",
            rationale="An unterminated escape sequence is undefined behaviour and may parse incorrectly.",
            tags=["expressions", "literals"],
            references=["MISRA C:2012 Rule 4.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["CharacterLiteral", "StringLiteral"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for kind in ("CharacterLiteral", "StringLiteral"):
            for node in graph.nodes_by_kind(kind):
                props = node.get("semantic_properties", {})
                terminated = props.get("escape_sequence_terminated")
                if not _meta_true(props.get("unterminated_escape")) and (
                    terminated is None or _meta_true(terminated)
                ):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation="A character or string literal contains an unterminated escape sequence.",
                        risk_description="Unterminated escapes are undefined behaviour.",
                        confidence_factors={
                            "ast_match_specificity": 0.95,
                            "type_information_complete": 0.9,
                            "macro_clarity": 0.95,
                            "historical_false_positive_rate": 0.05,
                            "fix_generator_certainty": 0.5,
                        },
                        confidence_score=0.9,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="terminate every octal/hex escape sequence",
                            rationale="Escape sequences must be syntactically complete.",
                            confidence_score=0.5,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=['char c = "\\x41";'],
            non_compliant=['char c = "\\x"; /* unterminated hex escape */'],
        )


class Rule7_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-7-1",
            rule_number="7.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Octal constants (other than zero) shall not be used",
            description="An integer constant shall not use octal notation except for zero.",
            rationale="Octal literals are easily misread because a leading zero looks like decimal zero padding.",
            tags=["expressions", "literals", "constants"],
            references=["MISRA C:2012 Rule 7.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["IntegerLiteral"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("IntegerLiteral"):
            props = node.get("semantic_properties", {})
            if props.get("literal_base") != "octal" and not _meta_true(props.get("octal_nonzero_constant")):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A non-zero octal integer constant is used.",
                    risk_description="Octal notation is error-prone and should be avoided.",
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
                        suggested_code="rewrite the constant in decimal or hexadecimal",
                        rationale="Use decimal or hex instead of octal notation.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t value = 10U;"],
            non_compliant=["uint16_t value = 010U; /* octal 8 */"],
        )


class Rule7_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-7-2",
            rule_number="7.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A 'u' or 'U' suffix shall be applied to unsigned integer constants",
            description="An integer constant with unsigned essential type shall include a u/U suffix.",
            rationale="Missing unsigned suffixes rely on implicit conversion rules that are easy to get wrong.",
            tags=["expressions", "literals", "essential-types"],
            references=["MISRA C:2012 Rule 7.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["IntegerLiteral"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.EXPRESSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        essential_types = self.essential_types()
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("IntegerLiteral"):
            props = node.get("semantic_properties", {})
            if not _meta_true(props.get("missing_u_suffix")):
                continue
            essential = essential_types.essential_type_of(node)
            if not essential.startswith("unsigned"):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Unsigned integer constant lacks a u/U suffix (essential type '{essential}').",
                    risk_description="Implicit typing of unsigned constants can cause unexpected conversions.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.88,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.08,
                        "fix_generator_certainty": 0.7,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="append a u or U suffix to the literal",
                        rationale="Unsigned constants should spell out their unsignedness explicitly.",
                        confidence_score=0.7,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint32_t mask = 0xFFFF0000U;"],
            non_compliant=["uint32_t mask = 0xFFFF0000; /* missing U suffix */"],
        )


class Rule7_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-7-3",
            rule_number="7.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The lowercase 'l' suffix shall not be used",
            description="The lowercase letter 'l' shall not be used in an integer constant suffix.",
            rationale="Lowercase 'l' is easily confused with the digit '1'.",
            tags=["expressions", "literals", "constants"],
            references=["MISRA C:2012 Rule 7.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["IntegerLiteral"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("IntegerLiteral"):
            if not _meta_true(node.get("semantic_properties", {}).get("uses_lowercase_l_suffix")):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="An integer constant uses the lowercase 'l' suffix.",
                    risk_description="Lowercase 'l' is visually indistinguishable from '1' in many fonts.",
                    confidence_factors={
                        "ast_match_specificity": 0.97,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.03,
                        "fix_generator_certainty": 0.8,
                    },
                    confidence_score=0.92,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use uppercase 'L' instead of lowercase 'l'",
                        rationale="Always use 'L' for long integer suffixes.",
                        confidence_score=0.8,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int64_t value = 1000LL;"],
            non_compliant=["int64_t value = 1000ll; /* lowercase l */"],
        )


class Rule12_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-12-1",
            rule_number="12.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The precedence of operators within expressions should be made explicit",
            description="Parentheses should be used where operator precedence is not immediately obvious.",
            rationale="Implicit precedence is a common source of review mistakes.",
            tags=["expressions", "precedence"],
            references=["MISRA C:2012 Rule 12.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.EXPRESSIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("BinaryOperator"):
            if not _meta_true(node.get("semantic_properties", {}).get("needs_explicit_parentheses")):
                continue
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Operator precedence in this '{opcode}' expression should be made explicit.",
                    risk_description="Unclear precedence can hide the author's intended evaluation order.",
                    confidence_factors={
                        "ast_match_specificity": 0.8,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.72,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="add parentheses to clarify operator precedence",
                        rationale="Make non-obvious precedence explicit with parentheses.",
                        confidence_score=0.45,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t value = (a + b) * c;"],
            non_compliant=["uint16_t value = a + b * c; /* precedence unclear */"],
        )


class Rule12_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-12-5",
            rule_number="12.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="The sizeof operator shall not be applied to a function parameter declared as an array",
            description="sizeof shall not be applied to a decayed array function parameter.",
            rationale="sizeof on a decayed array parameter yields pointer size, not array size.",
            tags=["expressions", "sizeof", "arrays"],
            references=["MISRA C:2012 Rule 12.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_expressions",
            requires_ast_nodes=["UnaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.EXPRESSIONS,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("UnaryOperator"):
            props = node.get("semantic_properties", {})
            if props.get("opcode") != "sizeof":
                continue
            if not _meta_true(props.get("sizeof_operand_is_decayed_array")):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="sizeof is applied to a decayed array function parameter.",
                    risk_description="The result is the pointer size, not the declared array extent.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="pass the array length as a separate parameter instead of using sizeof",
                        rationale="Do not use sizeof on a decayed array parameter.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void f(uint8_t buffer[10], size_t length) { (void)length; }"],
            non_compliant=["void f(uint8_t buffer[10]) { size_t n = sizeof(buffer); /* pointer size */ }"],
        )
