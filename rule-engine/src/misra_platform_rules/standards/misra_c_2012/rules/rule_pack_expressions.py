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
