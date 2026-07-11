"""Control Flow rule pack (Phase 3/4/5) — MISRA C:2012 Rules 2.1, 15.1, 15.6,
16.3, 16.4, 16.6, 16.2, 16.5, 17.4, 15.4. Reuses `CFGBuilder` for the
switch-fallthrough/loop-termination checks. Rule 2.1 (Phase 4) uses the real
basic-block `CFGEngine` instead, since unreachable-code detection genuinely
needs a sound CFG (goto/loop/switch aware), not the Phase 3 structural
heuristic. Rule 17.4 (Phase 5) also uses `CFGEngine` for a sound view of
every path into the function's exit. Rule 15.5 ships separately
(`rule_15_5.py`)."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


class Rule2_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-1",
            rule_number="2.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A project shall not contain unreachable code",
            description="Every statement in a function shall be reachable from its entry point.",
            rationale="Unreachable code cannot be exercised by testing and often signals a "
            "logic error (e.g. a misplaced return, or both branches of an if always returning).",
            tags=["control-flow", "cfg", "unreachable"],
            references=["MISRA C:2012 Rule 2.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["FunctionDecl"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
            requires_cfg=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            cfg = self.cfg_v2(function_node, graph, context)
            for block in cfg.unreachable_blocks():
                # Report once per unreachable block (its first statement),
                # rather than once per statement inside it, to avoid
                # swamping the reviewer with one finding per line of a
                # single unreachable region.
                first_statement = block.statements[0]
                results.append(
                    self.make_result(
                        context,
                        graph,
                        first_statement,
                        explanation="This code is unreachable: no path from the function's "
                        "entry point can reach it.",
                        risk_description="Unreachable code cannot be exercised by testing and "
                        "usually indicates a logic defect (e.g. code after an unconditional "
                        "return, or after both branches of an if/else already returned).",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.8,
                            "historical_false_positive_rate": 0.2,
                            "fix_generator_certainty": 0.2,
                        },
                        confidence_score=0.78,
                        suggested_fix=None,
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["if (ok) {\n    return 1;\n}\nreturn 0;"],
            non_compliant=[
                "return 1;\nlog_error(); /* unreachable: always follows the return */"
            ],
        )


class Rule15_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-1",
            rule_number="15.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The goto statement should not be used",
            description="The goto statement should not be used.",
            rationale="goto obscures control flow and complicates static analysis and review.",
            tags=["control-flow"],
            references=["MISRA C:2012 Rule 15.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["GotoStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("GotoStmt"):
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A goto statement is used.",
                    risk_description="goto-based control flow is harder to verify and maintain.",
                    confidence_factors={
                        "ast_match_specificity": 1.0,
                        "type_information_complete": 1.0,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="restructure control flow using loops/conditionals",
                        rationale="Replace goto with structured control flow where feasible.",
                        confidence_score=0.3,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["while (!done) {\n    /* ... */\n}"],
            non_compliant=["goto cleanup;\n/* ... */\ncleanup:\n    return;"],
        )


class Rule15_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-6",
            rule_number="15.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The body of an iteration or selection statement shall be a compound statement",
            description="Bodies of if/else/while/for/do statements shall be enclosed in braces.",
            rationale="Brace-less bodies are a classic source of dangling-statement defects.",
            tags=["control-flow", "style"],
            references=["MISRA C:2012 Rule 15.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["IfStmt", "WhileStmt", "ForStmt", "DoStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("IfStmt"):
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            then_branch = children[1]
            if then_branch.get("node_kind") != "CompoundStmt":
                results.append(self._violation(context, graph, node, "IfStmt (then)"))
            if len(children) >= 3:
                else_branch = children[2]
                # An "else if" chain is compliant without extra braces around
                # the nested if itself.
                if else_branch.get("node_kind") not in ("CompoundStmt", "IfStmt"):
                    results.append(self._violation(context, graph, node, "IfStmt (else)"))

        for kind in ("WhileStmt", "ForStmt"):
            for node in graph.nodes_by_kind(kind):
                children = graph.children(node["node_id"])
                if not children:
                    continue
                body = children[-1]
                if body.get("node_kind") != "CompoundStmt":
                    results.append(self._violation(context, graph, node, kind))

        for node in graph.nodes_by_kind("DoStmt"):
            children = graph.children(node["node_id"])
            if not children:
                continue
            if children[0].get("node_kind") != "CompoundStmt":
                results.append(self._violation(context, graph, node, "DoStmt"))
        return results

    def _violation(self, context: RuleContext, graph: AstGraph, node: dict, kind: str) -> RuleResult:
        return self.make_result(
            context,
            graph,
            node,
            explanation=f"{kind} body is a single statement, not a compound statement.",
            risk_description="Adding a second statement later without braces silently changes control flow.",
            confidence_factors={
                "ast_match_specificity": 0.9,
                "type_information_complete": 0.9,
                "macro_clarity": 0.9,
                "historical_false_positive_rate": 0.1,
                "fix_generator_certainty": 0.75,
            },
            confidence_score=0.85,
            suggested_fix=SuggestedFix(
                original_code=AstGraph.offending_text(node),
                suggested_code="wrap the body in { }",
                rationale="Braces make the statement's scope unambiguous.",
                confidence_score=0.75,
            ),
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["if (flag) {\n    do_thing();\n}"],
            non_compliant=["if (flag)\n    do_thing();"],
        )


class Rule16_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-16-3",
            rule_number="16.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="An unconditional break shall terminate every switch clause",
            description="Every switch clause shall end in an unconditional break, return, continue, or goto.",
            rationale="Fallthrough between switch clauses is rarely intentional and hard to review.",
            tags=["control-flow", "switch"],
            references=["MISRA C:2012 Rule 16.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["SwitchStmt", "CaseStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
            requires_cfg=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        cfg = self.cfg()
        results: list[RuleResult] = []

        for switch_node in graph.nodes_by_kind("SwitchStmt"):
            for case_node in cfg.switch_blocks_without_terminator(switch_node, graph):
                results.append(
                    self.make_result(
                        context,
                        graph,
                        case_node,
                        explanation="Switch clause falls through to the next clause without a break.",
                        risk_description="Unintended fallthrough is a common source of switch-statement defects.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.9,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.15,
                            "fix_generator_certainty": 0.6,
                        },
                        confidence_score=0.8,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(case_node),
                            suggested_code="add an explicit break at the end of this clause",
                            rationale="Terminate every switch clause unconditionally.",
                            confidence_score=0.6,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["case 1:\n    do_a();\n    break;"],
            non_compliant=["case 1:\n    do_a();\ncase 2:\n    do_b();\n    break;"],
        )


class Rule16_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-16-4",
            rule_number="16.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Every switch statement shall have a default label",
            description="Every switch statement shall contain a default clause.",
            rationale="An explicit default clause documents that unhandled cases were considered.",
            tags=["control-flow", "switch"],
            references=["MISRA C:2012 Rule 16.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["SwitchStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("SwitchStmt"):
            descendants = graph.descendants(node["node_id"])
            if any(d.get("node_kind") == "DefaultStmt" for d in descendants):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="Switch statement has no default clause.",
                    risk_description="Unhandled cases fail silently without a default clause.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.6,
                    },
                    confidence_score=0.87,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="add a default: clause",
                        rationale="Handle (or explicitly reject) every unlisted case value.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["switch (mode) {\ncase A: break;\ndefault: break;\n}"],
            non_compliant=["switch (mode) {\ncase A: break;\n}"],
        )


class Rule16_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-16-6",
            rule_number="16.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Every switch statement shall have at least two switch clauses",
            description="Every switch statement shall have at least two switch-labeled clauses.",
            rationale="A switch with fewer than two clauses should be an if statement.",
            tags=["control-flow", "switch"],
            references=["MISRA C:2012 Rule 16.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["SwitchStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("SwitchStmt"):
            descendants = graph.descendants(node["node_id"])
            clause_count = sum(1 for d in descendants if d.get("node_kind") in ("CaseStmt", "DefaultStmt"))
            if clause_count >= 2:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Switch statement has only {clause_count} clause(s).",
                    risk_description="A switch with fewer than two clauses is better expressed as an if.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.82,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="replace the switch with an if statement, or add more clauses",
                        rationale="Use switch only when it meaningfully improves readability over if.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["switch (mode) {\ncase A: break;\ncase B: break;\ndefault: break;\n}"],
            non_compliant=["switch (mode) {\ndefault: break;\n}"],
        )


class Rule16_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-16-2",
            rule_number="16.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A switch label shall only be used within the compound statement of a switch",
            description="A case/default label shall be a direct clause of its switch's own compound statement.",
            rationale="A label nested inside an extra block inside a switch is legal C but easily misread.",
            tags=["control-flow", "switch"],
            references=["MISRA C:2012 Rule 16.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["CaseStmt", "DefaultStmt", "SwitchStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.all_nodes():
            if node.get("node_kind") not in ("CaseStmt", "DefaultStmt"):
                continue
            parent = graph.get(node.get("parent_id", ""))
            grandparent = graph.get(parent.get("parent_id", "")) if parent else None
            if (
                parent is not None
                and parent.get("node_kind") == "CompoundStmt"
                and grandparent is not None
                and grandparent.get("node_kind") == "SwitchStmt"
            ):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="This switch label is not a direct clause of its switch's compound statement.",
                    risk_description="A label nested inside an extra block is legal C but hides the switch's real structure.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.35,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="move the label to be a direct clause of the switch's body",
                        rationale="Avoid nesting switch labels inside extra blocks.",
                        confidence_score=0.35,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["switch (mode) {\ncase A:\n    break;\ndefault:\n    break;\n}"],
            non_compliant=["switch (mode) {\n{\ncase A: /* nested inside an extra block */\n    break;\n}\ndefault:\n    break;\n}"],
        )


class Rule16_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-16-5",
            rule_number="16.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A default label shall appear either as the first or as the last switch label",
            description="If a switch statement has a default clause, it shall be the first or last clause listed.",
            rationale="A default clause buried in the middle is easy to overlook when scanning the cases.",
            tags=["control-flow", "switch"],
            references=["MISRA C:2012 Rule 16.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["SwitchStmt", "DefaultStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for switch_node in graph.nodes_by_kind("SwitchStmt"):
            body_candidates = [
                child for child in graph.children(switch_node["node_id"]) if child.get("node_kind") == "CompoundStmt"
            ]
            if not body_candidates:
                continue
            clauses = [
                child
                for child in graph.children(body_candidates[0]["node_id"])
                if child.get("node_kind") in ("CaseStmt", "DefaultStmt")
            ]
            default_positions = [i for i, clause in enumerate(clauses) if clause.get("node_kind") == "DefaultStmt"]
            if not default_positions:
                continue
            position = default_positions[0]
            if position in (0, len(clauses) - 1):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    clauses[position],
                    explanation=(
                        f"The default clause is clause {position + 1} of {len(clauses)}, "
                        "neither first nor last."
                    ),
                    risk_description="A default clause buried among case clauses is easy to miss during review.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code="default:",
                        suggested_code="move the default clause to be first or last",
                        rationale="Place default where reviewers expect to find it.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["switch (mode) {\ncase A: break;\ncase B: break;\ndefault: break;\n}"],
            non_compliant=["switch (mode) {\ncase A: break;\ndefault: break;\ncase B: break;\n}"],
        )


class Rule17_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-4",
            rule_number="17.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="All exit paths from a function with non-void return type shall have an explicit return value",
            description="Every path from a non-void function's entry to its exit shall pass through a return statement that yields a value.",
            rationale="Falling off the end of a non-void function, or a bare 'return;', produces an unspecified value.",
            tags=["control-flow", "cfg", "functions"],
            references=["MISRA C:2012 Rule 17.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["FunctionDecl", "ReturnStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
            requires_cfg=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            has_body = any(
                child.get("node_kind") == "CompoundStmt" for child in graph.children(function_node["node_id"])
            )
            if not has_body:
                continue
            return_type = function_node.get("essential_type", "unknown")
            if return_type in ("unknown", "void"):
                # A void function has nothing to check; "unknown" means we
                # cannot soundly tell, so we deliberately avoid guessing.
                continue

            cfg = self.cfg_v2(function_node, graph, context)
            offending = None
            for edge in cfg.exit_edges():
                block = cfg.blocks.get(edge.source)
                if edge.kind != "return":
                    offending = block.statements[-1] if block and block.statements else function_node
                    break
                last_statement = block.statements[-1] if block and block.statements else None
                if last_statement is None or not graph.children(last_statement["node_id"]):
                    offending = last_statement or function_node
                    break
            if offending is None:
                continue

            name = function_node.get("semantic_properties", {}).get("name", "<anonymous>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    offending,
                    explanation=(
                        f"Function '{name}' (essential type '{return_type}') has a path reaching its "
                        "exit without an explicit return value."
                    ),
                    risk_description="A missing return value on some path yields an unspecified result to the caller.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.8,
                    suggested_fix=None,
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t clamp(int32_t v) {\n    if (v < 0) {\n        return 0;\n    }\n    return v;\n}"],
            non_compliant=["int32_t clamp(int32_t v) {\n    if (v < 0) {\n        return 0;\n    }\n    /* falls off the end for v >= 0 */\n}"],
        )


class Rule15_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-4",
            rule_number="15.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="There should be no more than one break or goto statement used to terminate any given loop",
            description="A single loop should be terminated by at most one break/goto statement.",
            rationale="Multiple exit statements for one loop make its termination condition harder to verify.",
            tags=["control-flow", "loops"],
            references=["MISRA C:2012 Rule 15.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["ForStmt", "WhileStmt", "DoStmt", "BreakStmt", "GotoStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
            requires_cfg=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        cfg = self.cfg()
        results: list[RuleResult] = []

        for kind in ("ForStmt", "WhileStmt", "DoStmt"):
            for loop_node in graph.nodes_by_kind(kind):
                terminators = cfg.loop_termination_statements(loop_node, graph)
                if len(terminators) <= 1:
                    continue
                for terminator in terminators[1:]:
                    results.append(
                        self.make_result(
                            context,
                            graph,
                            terminator,
                            explanation=(
                                f"This loop is terminated by {len(terminators)} separate "
                                "break/goto statements."
                            ),
                            risk_description="Multiple loop-exit points make the loop's termination logic harder to verify.",
                            confidence_factors={
                                "ast_match_specificity": 0.8,
                                "type_information_complete": 0.8,
                                "macro_clarity": 0.85,
                                "historical_false_positive_rate": 0.2,
                                "fix_generator_certainty": 0.3,
                            },
                            confidence_score=0.72,
                            suggested_fix=None,
                        )
                    )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["while (!done) {\n    if (error) {\n        done = true;\n    }\n}"],
            non_compliant=[
                "while (1) {\n    if (a) {\n        break;\n    }\n    if (b) {\n        break; /* second exit */\n    }\n}"
            ],
        )


def _enclosing_scope_chain(node: dict, graph: AstGraph) -> list[str]:
    """Block-scope ancestry of `node` (its own scope id, then every
    enclosing scope id, ending at file scope) — shared by Rule15_2 and
    Rule15_3 so the "same or enclosing block" test is defined exactly once
    rather than duplicated between the goto-side and label-side rules."""
    chain: list[str] = []
    current_id = node.get("parent_id", "")
    while current_id:
        chain.append(current_id)
        parent = graph.get(current_id)
        if not parent:
            break
        current_id = parent.get("parent_id", "")
    return chain


def _goto_label_pairs_crossing_scope(
    function_node: dict, graph: AstGraph
) -> list[tuple[dict, dict]]:
    """(goto, label) pairs, within one function, where the label's scope is
    *not* the goto's own scope and *not* one of the goto's enclosing scopes
    — i.e. the goto would have to jump into a scope it is not already
    lexically inside of. Shared detection engine for Rule15_2/Rule15_3."""
    labels_by_name: dict[str, dict] = {
        label.get("semantic_properties", {}).get("name", ""): label
        for label in graph.descendants(function_node["node_id"])
        if label.get("node_kind") == "LabelStmt"
    }
    violations: list[tuple[dict, dict]] = []
    for goto in graph.descendants(function_node["node_id"]):
        if goto.get("node_kind") != "GotoStmt":
            continue
        target_name = goto.get("semantic_properties", {}).get("target_label", "")
        label = labels_by_name.get(target_name)
        if label is None:
            continue  # unresolved target; not this rule's concern
        goto_scope_chain = [goto.get("parent_id", ""), *_enclosing_scope_chain(goto, graph)]
        label_scope = label.get("parent_id", "")
        if label_scope not in goto_scope_chain:
            violations.append((goto, label))
    return violations


class Rule15_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-2",
            rule_number="15.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A goto statement shall jump to a label in the same or an enclosing block",
            description="A goto shall not jump into a block it is not already lexically inside of.",
            rationale="Jumping into a nested block skips that block's own initialization, which is unsound.",
            tags=["control-flow", "goto"],
            references=["MISRA C:2012 Rule 15.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["FunctionDecl", "GotoStmt", "LabelStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            for goto, label in _goto_label_pairs_crossing_scope(function_node, graph):
                target_name = goto.get("semantic_properties", {}).get("target_label", "")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        goto,
                        explanation=f"'goto {target_name}' jumps into a block that does not enclose it.",
                        risk_description="Jumping into a nested block skips that block's own "
                        "initialization, which is unsound.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.2,
                        },
                        confidence_score=0.82,
                        suggested_fix=None,
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void f(int32_t x) {\n    if (x < 0) {\n        goto cleanup;\n    }\n    cleanup:\n    release();\n}"],
            non_compliant=["void f(void) {\n    goto inner; /* jumps into the if-block below */\n    if (1) {\n        inner:\n        release();\n    }\n}"],
        )


class Rule15_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-3",
            rule_number="15.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Any label referenced by a goto statement shall be declared in the same or an enclosing block",
            description="A label's scope must already enclose every goto that targets it.",
            rationale="A label placed in a block the goto cannot see forces the jump to skip "
            "that block's initialization, which is unsound.",
            tags=["control-flow", "goto", "labels"],
            references=["MISRA C:2012 Rule 15.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["FunctionDecl", "GotoStmt", "LabelStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            for goto, label in _goto_label_pairs_crossing_scope(function_node, graph):
                label_name = label.get("semantic_properties", {}).get("name", "")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        label,
                        explanation=f"Label '{label_name}' is declared in a block that does not "
                        "enclose one of the goto statements referencing it.",
                        risk_description="A goto targeting this label would skip this block's own "
                        "initialization, which is unsound.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.2,
                        },
                        confidence_score=0.82,
                        suggested_fix=None,
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void f(int32_t x) {\n    if (x < 0) {\n        goto cleanup;\n    }\n    cleanup:\n    release();\n}"],
            non_compliant=["void f(void) {\n    goto inner;\n    if (1) {\n        inner: /* not visible to the goto above */\n        release();\n    }\n}"],
        )


class Rule15_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-15-7",
            rule_number="15.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="An if-else-if construct shall be terminated with an else clause",
            description="Every if / else-if chain shall end with a final else clause.",
            rationale="A missing final else silently drops the case where none of the "
            "conditions hold.",
            tags=["control-flow", "if"],
            references=["MISRA C:2012 Rule 15.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["IfStmt"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("IfStmt"):
            # Only the outermost `if` of a chain should be reported; an
            # `else if` is itself an IfStmt whose parent is the enclosing
            # IfStmt's else-branch, so skip those to report the chain once.
            parent = graph.get(node.get("parent_id", ""))
            if parent is not None and parent.get("node_kind") == "IfStmt" and self._is_else_branch(node, parent, graph):
                continue

            chain_end = self._final_else_if(node, graph)
            if chain_end is None:
                continue  # not actually an else-if chain (no else at all is fine on its own)
            if self._has_final_else(chain_end, graph):
                continue

            results.append(
                self.make_result(
                    context,
                    graph,
                    chain_end,
                    explanation="This if-else-if chain has no final else clause.",
                    risk_description="A missing final else silently drops the case where none "
                    "of the conditions hold.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.78,
                    suggested_fix=SuggestedFix(
                        original_code="if (...) { ... } else if (...) { ... }",
                        suggested_code="if (...) { ... } else if (...) { ... } else { /* handle the "
                        "remaining case */ }",
                        rationale="Add a final else to handle every remaining case explicitly.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    @staticmethod
    def _is_else_branch(node: dict, parent: dict, graph: AstGraph) -> bool:
        children = graph.children(parent["node_id"])
        return len(children) >= 3 and children[-1].get("node_id") == node.get("node_id")

    @staticmethod
    def _final_else_if(node: dict, graph: AstGraph) -> dict | None:
        """Walks an if -> else-if -> else-if chain to its last link, or
        `None` if this `if` has no else branch at all (not a chain)."""
        current = node
        found_chain = False
        while True:
            children = graph.children(current["node_id"])
            if len(children) < 3:
                return current if found_chain else None
            else_branch = children[-1]
            if else_branch.get("node_kind") != "IfStmt":
                return current if found_chain else None
            found_chain = True
            current = else_branch

    @staticmethod
    def _has_final_else(node: dict, graph: AstGraph) -> bool:
        children = graph.children(node["node_id"])
        if len(children) < 3:
            return False
        return children[-1].get("node_kind") != "IfStmt"

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=[
                "if (mode == 0) {\n    a();\n} else if (mode == 1) {\n    b();\n} else {\n    c();\n}"
            ],
            non_compliant=["if (mode == 0) {\n    a();\n} else if (mode == 1) {\n    b();\n}"],
        )


class Rule14_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-14-2",
            rule_number="14.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A for loop shall be well-formed",
            description="A for statement shall declare an initialization, a condition, and an "
            "increment expression.",
            rationale="Omitting one of the three for-loop clauses hides the loop's control "
            "structure in the body, making it harder to verify termination.",
            tags=["control-flow", "loops", "for"],
            references=["MISRA C:2012 Rule 14.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_control_flow",
            requires_ast_nodes=["ForStmt"],
            implementation_category=RuleImplementationCategory.C_CONTROL_FLOW,
            rule_pack=RulePack.CONTROL_FLOW,
        )

    _EXPECTED_CLAUSES = 4  # init, condition, increment, body

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("ForStmt"):
            children = graph.children(node["node_id"])
            if len(children) >= self._EXPECTED_CLAUSES:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="This for loop is missing its initialization, condition, or "
                    "increment expression.",
                    risk_description="Omitting one of the three for-loop clauses hides the "
                    "loop's control structure in the body, making it harder to verify "
                    "termination.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code="for (...; ...) { ... }",
                        suggested_code="for (init; condition; increment) { ... }",
                        rationale="Give every for loop an explicit init, condition, and "
                        "increment clause.",
                        confidence_score=0.3,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["for (i = 0; i < 10; i++) {\n    process(i);\n}"],
            non_compliant=["for (i = 0; i < 10;) {\n    process(i);\n    i++; /* increment hidden in the body */\n}"],
        )
