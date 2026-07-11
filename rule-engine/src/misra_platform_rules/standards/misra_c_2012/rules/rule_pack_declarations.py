"""Declarations rule pack (Phase 3/5/6) — MISRA C:2012 Rules 8.2, 8.6, 8.14,
5.2, 5.3, 2.7, and (Phase 6) 2.3, 2.4, 5.5, 5.6, 5.7, 8.1, 17.3, 17.6, 18.7,
19.2. Rule 8.4 ships separately (`rule_8_4.py`, upgraded in Phase 3 to also
use `LinkageIndex`). Every rule here reuses `SymbolIndex`/`MacroAnalyzer`
rather than re-deriving scope/usage/macro-table logic inline."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


class Rule8_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-2",
            rule_number="8.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Function types shall be in prototype form with named parameters",
            description="Every function parameter shall have a name in its declaration.",
            rationale="Unnamed parameters in a prototype hide intent and hinder review.",
            tags=["declarations", "functions"],
            references=["MISRA C:2012 Rule 8.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["FunctionDecl", "ParmVarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("FunctionDecl"):
            params = [child for child in graph.children(node["node_id"]) if child.get("node_kind") == "ParmVarDecl"]
            unnamed = [p for p in params if not p.get("semantic_properties", {}).get("name")]
            if not unnamed:
                continue
            name = node.get("semantic_properties", {}).get("name", "<anonymous>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Function '{name}' declares {len(unnamed)} parameter(s) without a name.",
                    risk_description="Unnamed parameters make the interface harder to review and document.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code=f"give every parameter of '{name}' an explicit name",
                        rationale="Named parameters document intent and enable static analysis.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void set_speed(uint16_t speed_kph);"],
            non_compliant=["void set_speed(uint16_t);"],
        )


class Rule8_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-6",
            rule_number="8.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="An identifier with external linkage shall have exactly one definition",
            description=(
                "An object or function with external linkage shall have a single definition "
                "across the whole program."
            ),
            rationale="Multiple definitions of an externally-linked symbol violate the one-definition rule.",
            tags=["linkage", "declarations", "cross-tu"],
            references=["MISRA C:2012 Rule 8.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.DECLARATIONS,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        linkage = self.linkage(context)
        results: list[RuleResult] = []
        reported: set[str] = set()

        for kind in ("FunctionDecl", "VarDecl"):
            for node in graph.nodes_by_kind(kind):
                name = node.get("semantic_properties", {}).get("name", "")
                if not name or name in reported or not graph.is_file_scope(node["node_id"]):
                    continue
                if linkage.data.get("symbols") and not linkage.has_multiple_definitions(name):
                    continue
                if not linkage.data.get("symbols"):
                    # No project-wide linkage index available (single-TU context);
                    # cannot make a sound cross-TU determination.
                    continue
                reported.add(name)
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"External identifier '{name}' has a definition in more than one "
                            "translation unit."
                        ),
                        risk_description="One-definition-rule violations cause undefined linker behaviour.",
                        confidence_factors={
                            "ast_match_specificity": 0.9,
                            "type_information_complete": 0.8,
                            "macro_clarity": 0.9,
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
            compliant=["/* a.c */\nvoid init(void) { /* ... */ }"],
            non_compliant=[
                "/* a.c */\nvoid init(void) { /* ... */ }\n/* b.c */\nvoid init(void) { /* duplicate */ }"
            ],
        )


class Rule8_14(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-14",
            rule_number="8.14",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The restrict qualifier shall not be used",
            description="The restrict type qualifier shall not be used.",
            rationale="restrict-qualified aliasing assumptions are easy to violate undetected.",
            tags=["declarations", "qualifiers"],
            references=["MISRA C:2012 Rule 8.14"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["ParmVarDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        qualifiers = self.qualifiers()
        results: list[RuleResult] = []

        for node in graph.all_nodes():
            if not qualifiers.has_qualifier(node, "restrict"):
                continue
            name = node.get("semantic_properties", {}).get("name", "<unnamed>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'{name}' is declared with the restrict qualifier.",
                    risk_description="restrict aliasing violations are undefined behaviour and hard to detect.",
                    confidence_factors={
                        "ast_match_specificity": 0.97,
                        "type_information_complete": 0.95,
                        "macro_clarity": 0.98,
                        "historical_false_positive_rate": 0.02,
                        "fix_generator_certainty": 0.7,
                    },
                    confidence_score=0.95,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code=f"remove the restrict qualifier from '{name}'",
                        rationale="Avoid the restrict qualifier entirely.",
                        confidence_score=0.7,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void copy(uint8_t *dest, const uint8_t *src, size_t n);"],
            non_compliant=["void copy(uint8_t *restrict dest, const uint8_t *restrict src, size_t n);"],
        )


class Rule5_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-2",
            rule_number="5.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Identifiers declared in the same scope shall be distinct",
            description=(
                "An identifier shall not collide with another identifier declared in a "
                "different namespace (tag, member, or ordinary) if that ambiguity could "
                "confuse a reader."
            ),
            rationale="Reusing a spelling across namespaces (e.g. a tag and a variable) "
            "confuses readers even though the compiler accepts it.",
            tags=["declarations", "identifiers"],
            references=["MISRA C:2012 Rule 5.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["VarDecl", "RecordDecl", "EnumDecl", "TypedefDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []
        reported: set[frozenset[str]] = set()

        for first, second in symbols.cross_namespace_collisions():
            key = frozenset((first["node_id"], second["node_id"]))
            if key in reported:
                continue
            reported.add(key)
            name = first.get("semantic_properties", {}).get("name", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    second,
                    explanation=(
                        f"'{name}' is declared as a {first.get('node_kind')} and also as a "
                        f"{second.get('node_kind')}, colliding across identifier namespaces."
                    ),
                    risk_description="Cross-namespace name reuse is confusing even though it compiles.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code=name,
                        suggested_code=f"rename one of the two declarations of '{name}'",
                        rationale="Give every declaration a distinct spelling regardless of namespace.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct point_tag { int32_t x; int32_t y; };\nstruct point_tag origin;"],
            non_compliant=["struct point { int32_t x; int32_t y; };\nint32_t point; /* collides with tag */"],
        )


class Rule5_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-3",
            rule_number="5.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="An identifier declared in an inner scope shall not hide an outer one",
            description="An identifier in an inner scope shall not have the same spelling as one in an enclosing scope.",
            rationale="Shadowing makes it easy to accidentally reference the wrong variable.",
            tags=["declarations", "identifiers", "scope"],
            references=["MISRA C:2012 Rule 5.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["VarDecl", "ParmVarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []

        for outer, inner in symbols.shadowing_pairs():
            if outer.get("node_kind") not in ("VarDecl", "ParmVarDecl", "FunctionDecl"):
                continue
            if inner.get("node_kind") not in ("VarDecl", "ParmVarDecl"):
                continue
            name = inner.get("semantic_properties", {}).get("name", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    inner,
                    explanation=f"'{name}' hides an identifier of the same name declared in an enclosing scope.",
                    risk_description="A reader (or the author) may mistake the inner declaration for the outer one.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.55,
                    },
                    confidence_score=0.82,
                    suggested_fix=SuggestedFix(
                        original_code=name,
                        suggested_code=f"rename the inner '{name}' to a distinct identifier",
                        rationale="Avoid shadowing an outer-scope declaration.",
                        confidence_score=0.55,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=[
                "int32_t count;\nvoid f(void) {\n    int32_t inner_count;\n    inner_count = count;\n}"
            ],
            non_compliant=["int32_t count;\nvoid f(void) {\n    int32_t count; /* hides the outer count */\n}"],
        )


class Rule2_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-7",
            rule_number="2.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="There should be no unused parameters in functions",
            description="Every function parameter should be referenced somewhere in the function body.",
            rationale="Unused parameters often signal an incomplete implementation or a stale interface.",
            tags=["declarations", "functions", "unused"],
            references=["MISRA C:2012 Rule 2.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["FunctionDecl", "ParmVarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []

        for function_node in graph.nodes_by_kind("FunctionDecl"):
            has_body = any(
                child.get("node_kind") == "CompoundStmt" for child in graph.children(function_node["node_id"])
            )
            if not has_body:
                continue  # a prototype has no body to check usage against
            params = [
                child
                for child in graph.children(function_node["node_id"])
                if child.get("node_kind") == "ParmVarDecl"
            ]
            for param in params:
                name = param.get("semantic_properties", {}).get("name", "")
                if not name or symbols.is_referenced(param, graph):
                    continue
                function_name = function_node.get("semantic_properties", {}).get("name", "<anonymous>")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        param,
                        explanation=f"Parameter '{name}' of function '{function_name}' is never used.",
                        risk_description="An unused parameter may indicate dead logic or a forgotten implementation.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.2,
                            "fix_generator_certainty": 0.3,
                        },
                        confidence_score=0.75,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code=f"(void){name}; /* or remove the parameter if truly unneeded */",
                            rationale="Reference the parameter explicitly, or remove it from the signature.",
                            confidence_score=0.3,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void log_event(uint8_t code) {\n    record(code);\n}"],
            non_compliant=["void log_event(uint8_t code) {\n    record(0); /* 'code' is never used */\n}"],
        )


class Rule2_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-3",
            rule_number="2.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A project should not contain unused type declarations",
            description="Every typedef name declared should be used as a type somewhere in the project.",
            rationale="An unused typedef is dead declarative clutter that hinders review.",
            tags=["declarations", "unused", "typedef"],
            references=["MISRA C:2012 Rule 2.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["TypedefDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("TypedefDecl"):
            name = node.get("semantic_properties", {}).get("name", "")
            if not name or symbols.is_referenced(node, graph):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Typedef '{name}' is declared but never used as a type.",
                    risk_description="Unused typedefs are dead declarative clutter that hinders review.",
                    confidence_factors={
                        "ast_match_specificity": 0.8,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.3,
                    },
                    confidence_score=0.7,
                    suggested_fix=SuggestedFix(
                        original_code=name,
                        suggested_code=f"remove the unused typedef '{name}'",
                        rationale="Delete typedefs that no declaration actually uses.",
                        confidence_score=0.3,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["typedef uint16_t speed_kph_t;\nspeed_kph_t current_speed;"],
            non_compliant=["typedef uint16_t speed_kph_t; /* never used as a type anywhere */"],
        )


class Rule2_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-4",
            rule_number="2.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A project should not contain unused tag declarations",
            description="Every struct/union/enum tag declared should be used as a type somewhere.",
            rationale="An unused tag declaration is dead declarative clutter that hinders review.",
            tags=["declarations", "unused", "tags"],
            references=["MISRA C:2012 Rule 2.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["RecordDecl", "EnumDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []

        for kind in ("RecordDecl", "EnumDecl"):
            for node in graph.nodes_by_kind(kind):
                name = node.get("semantic_properties", {}).get("name", "")
                if not name or symbols.is_referenced(node, graph):
                    continue
                tag_word = "union" if node.get("semantic_properties", {}).get("record_kind") == "union" else (
                    "struct" if kind == "RecordDecl" else "enum"
                )
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=f"Tag '{tag_word} {name}' is declared but never used as a type.",
                        risk_description="Unused tag declarations are dead declarative clutter that hinders review.",
                        confidence_factors={
                            "ast_match_specificity": 0.8,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.25,
                            "fix_generator_certainty": 0.3,
                        },
                        confidence_score=0.7,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code=f"remove the unused tag '{tag_word} {name}'",
                            rationale="Delete tags that no declaration actually uses.",
                            confidence_score=0.3,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct point_tag { int32_t x; int32_t y; };\nstruct point_tag origin;"],
            non_compliant=["struct point_tag { int32_t x; int32_t y; }; /* never used anywhere */"],
        )


class Rule5_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-5",
            rule_number="5.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Identifiers shall be distinct from macro names",
            description="No declared identifier shall have the same spelling as a #define'd macro name.",
            rationale="Reusing a macro's spelling as an identifier is confusing at every use site.",
            tags=["declarations", "identifiers", "macros"],
            references=["MISRA C:2012 Rule 5.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["VarDecl", "FunctionDecl", "TypedefDecl"],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        macros = self.macros()
        macro_names = {m.get("name", "") for m in macros.macro_definitions(context.macro_table)}
        macro_names.discard("")
        results: list[RuleResult] = []

        for name in symbols.all_names():
            if name not in macro_names:
                continue
            for decl in symbols.declarations(name):
                results.append(
                    self.make_result(
                        context,
                        graph,
                        decl,
                        explanation=f"'{name}' is declared as an identifier and also #define'd as a macro.",
                        risk_description="Readers cannot tell from a use site whether the macro or the "
                        "declaration is in effect.",
                        confidence_factors={
                            "ast_match_specificity": 0.9,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.6,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.8,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code=f"rename either the macro or the declaration of '{name}'",
                            rationale="Give the macro and the identifier distinct spellings.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define MAX_SPEED_KPH 250\nuint16_t current_speed_kph;"],
            non_compliant=["#define current_speed_kph 0\nuint16_t current_speed_kph; /* collides */"],
        )


class Rule5_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-6",
            rule_number="5.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A typedef name shall be a unique identifier",
            description="A typedef name shall not be reused for any other declaration.",
            rationale="Reusing a typedef's spelling for something else defeats its documentation value.",
            tags=["declarations", "identifiers", "typedef"],
            references=["MISRA C:2012 Rule 5.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["TypedefDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []
        reported: set[frozenset[str]] = set()

        for node in graph.nodes_by_kind("TypedefDecl"):
            name = node.get("semantic_properties", {}).get("name", "")
            if not name:
                continue
            for other in symbols.declarations(name):
                if other.get("node_id") == node.get("node_id"):
                    continue
                key = frozenset((node["node_id"], other["node_id"]))
                if key in reported:
                    continue
                reported.add(key)
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=f"Typedef name '{name}' collides with another declaration of the "
                        f"same spelling ({other.get('node_kind')}).",
                        risk_description="A non-unique typedef name can be silently shadowed or misread.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.8,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.15,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.75,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code=f"rename the typedef '{name}' to a unique spelling",
                            rationale="Typedef names must not collide with any other declaration.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["typedef uint16_t speed_kph_t;\nspeed_kph_t current_speed;"],
            non_compliant=["typedef uint16_t speed_kph_t;\nint32_t speed_kph_t; /* collides with the typedef */"],
        )


class Rule5_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-7",
            rule_number="5.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A tag name shall be a unique identifier",
            description="A struct/union/enum tag name shall not be reused for any other declaration.",
            rationale="Reusing a tag's spelling for something else defeats its documentation value.",
            tags=["declarations", "identifiers", "tags"],
            references=["MISRA C:2012 Rule 5.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["RecordDecl", "EnumDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []
        reported: set[frozenset[str]] = set()

        for kind in ("RecordDecl", "EnumDecl"):
            for node in graph.nodes_by_kind(kind):
                name = node.get("semantic_properties", {}).get("name", "")
                if not name:
                    continue
                for other in symbols.declarations(name):
                    if other.get("node_id") == node.get("node_id"):
                        continue
                    key = frozenset((node["node_id"], other["node_id"]))
                    if key in reported:
                        continue
                    reported.add(key)
                    results.append(
                        self.make_result(
                            context,
                            graph,
                            node,
                            explanation=f"Tag name '{name}' collides with another declaration of the "
                            f"same spelling ({other.get('node_kind')}).",
                            risk_description="A non-unique tag name can be silently shadowed or misread.",
                            confidence_factors={
                                "ast_match_specificity": 0.85,
                                "type_information_complete": 0.8,
                                "macro_clarity": 0.9,
                                "historical_false_positive_rate": 0.15,
                                "fix_generator_certainty": 0.4,
                            },
                            confidence_score=0.75,
                            suggested_fix=SuggestedFix(
                                original_code=name,
                                suggested_code=f"rename the tag '{name}' to a unique spelling",
                                rationale="Tag names must not collide with any other declaration.",
                                confidence_score=0.4,
                            ),
                        )
                    )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct point_tag { int32_t x; int32_t y; };\nstruct point_tag origin;"],
            non_compliant=["struct point_tag { int32_t x; };\nint32_t point_tag; /* collides with the tag */"],
        )


class Rule8_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-1",
            rule_number="8.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Types shall be explicitly specified",
            description="Every declaration shall explicitly state its type; implicit int is not permitted.",
            rationale="Implicit typing hides the author's intent and is easy to get wrong.",
            tags=["declarations", "types"],
            references=["MISRA C:2012 Rule 8.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["VarDecl", "FunctionDecl", "ParmVarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("VarDecl", "FunctionDecl", "ParmVarDecl"):
            for node in graph.nodes_by_kind(kind):
                if not node.get("semantic_properties", {}).get("implicit_type"):
                    continue
                name = node.get("semantic_properties", {}).get("name", "<unnamed>")
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=f"'{name}' is declared without an explicit type (implicit int).",
                        risk_description="Implicit typing hides the author's intent and is easy to get wrong.",
                        confidence_factors={
                            "ast_match_specificity": 0.95,
                            "type_information_complete": 0.7,
                            "macro_clarity": 0.95,
                            "historical_false_positive_rate": 0.05,
                            "fix_generator_certainty": 0.6,
                        },
                        confidence_score=0.9,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code=f"give '{name}' an explicit type",
                            rationale="Every declaration should spell out its type.",
                            confidence_score=0.6,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t counter;"],
            non_compliant=["counter; /* implicit int */"],
        )


class Rule17_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-3",
            rule_number="17.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="A function shall not be declared implicitly",
            description="Every function call shall be preceded by a visible declaration/prototype.",
            rationale="Implicitly-declared functions default to an assumed signature, which is unsound.",
            tags=["declarations", "functions"],
            references=["MISRA C:2012 Rule 17.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            if not node.get("semantic_properties", {}).get("implicit_declaration"):
                continue
            callee = node.get("semantic_properties", {}).get("callee", "<callee>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'{callee}' is called with no visible declaration, so it is "
                    "implicitly declared.",
                    risk_description="An implicitly-declared function defaults to an assumed "
                    "signature, which is unsound.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=f"{callee}(...)",
                        suggested_code=f"add a prototype for '{callee}' before this call",
                        rationale="Every called function must have a visible declaration.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t compute(int32_t x);\nvoid f(void) {\n    compute(1);\n}"],
            non_compliant=["void f(void) {\n    compute(1); /* no prototype visible */\n}"],
        )


class Rule17_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-6",
            rule_number="17.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="The declaration of an array parameter shall not contain the static keyword",
            description="An array-typed function parameter shall not be declared with the static keyword.",
            rationale="A `static` array-size hint constrains callers in a way that is easy to violate "
            "undetected.",
            tags=["declarations", "functions", "arrays"],
            references=["MISRA C:2012 Rule 17.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["ParmVarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("ParmVarDecl"):
            properties = node.get("semantic_properties", {})
            if not properties.get("is_array") or not properties.get("array_static"):
                continue
            name = properties.get("name", "<param>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Array parameter '{name}' is declared with the static keyword.",
                    risk_description="A static array-size hint constrains callers in a way that is "
                    "easy to violate undetected.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.7,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=f"static {name}[]",
                        suggested_code=f"remove the static keyword from '{name}'",
                        rationale="Do not use the static array-parameter form.",
                        confidence_score=0.7,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void process(uint8_t buffer[10]);"],
            non_compliant=["void process(uint8_t buffer[static 10]);"],
        )


class Rule18_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-18-7",
            rule_number="18.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Flexible array members shall not be declared",
            description="A struct's last member shall not be an incomplete flexible array member.",
            rationale="Flexible array members make an object's size implicit and easy to get wrong.",
            tags=["declarations", "arrays", "structs"],
            references=["MISRA C:2012 Rule 18.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["FieldDecl", "RecordDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("FieldDecl"):
            if not node.get("semantic_properties", {}).get("is_flexible_array_member"):
                continue
            record = graph.get(node.get("parent_id", ""))
            record_name = record.get("semantic_properties", {}).get("name", "<anonymous>") if record else "<anonymous>"
            field_name = node.get("semantic_properties", {}).get("name", "<field>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'{field_name}' in 'struct {record_name}' is a flexible array member.",
                    risk_description="Flexible array members make an object's size implicit and easy "
                    "to get wrong.",
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=f"{field_name}[]",
                        suggested_code="use a separately-allocated buffer with an explicit length field",
                        rationale="Avoid flexible array members entirely.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct frame_tag {\n    uint16_t length;\n    uint8_t *payload;\n};"],
            non_compliant=["struct frame_tag {\n    uint16_t length;\n    uint8_t payload[]; /* flexible array member */\n};"],
        )


class Rule19_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-19-2",
            rule_number="19.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The union keyword should not be used",
            description="A union type should not be declared.",
            rationale="Unions permit reading an object through a member other than the one last written, "
            "an unsafe type-punning idiom.",
            tags=["declarations", "unions"],
            references=["MISRA C:2012 Rule 19.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_declarations",
            requires_ast_nodes=["RecordDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.DECLARATIONS,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("RecordDecl"):
            if node.get("semantic_properties", {}).get("record_kind") != "union":
                continue
            name = node.get("semantic_properties", {}).get("name", "<anonymous>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'union {name}' is declared.",
                    risk_description="Unions permit reading an object through a member other than the "
                    "one last written, an unsafe type-punning idiom.",
                    confidence_factors={
                        "ast_match_specificity": 0.97,
                        "type_information_complete": 0.9,
                        "macro_clarity": 0.97,
                        "historical_false_positive_rate": 0.03,
                        "fix_generator_certainty": 0.2,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=f"union {name}",
                        suggested_code=f"replace 'union {name}' with a struct, or a documented "
                        "toolchain-specific alternative",
                        rationale="Avoid the union keyword entirely.",
                        confidence_score=0.2,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["struct variant_tag {\n    uint8_t tag;\n    int32_t value;\n};"],
            non_compliant=["union variant_tag {\n    int32_t as_int;\n    float as_float;\n};"],
        )
