"""Linkage rule pack (Phase 3/5) — MISRA C:2012 Rules 5.1, 8.7, 8.10, 5.8,
5.9, 8.5, 8.8. All cross-TU checks reuse `LinkageIndex`
(`RuleContext.cross_tu_linkage`, populated once per project run — see
`LinkageIndex.build`). Single-TU checks (5.9's within-TU half, 8.8) reuse
`SymbolIndex`. Rule 8.4 ships separately (`rule_8_4.py`) and was upgraded in
Phase 3 to also consult `LinkageIndex` when it is available."""

from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_SIGNIFICANT_CHARS = 31  # ISO C99 minimum significant external-identifier length


class Rule5_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-1",
            rule_number="5.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="External identifiers shall be distinct",
            description=(
                f"External identifiers shall be distinct within the first {_SIGNIFICANT_CHARS} "
                "significant characters, across the whole program."
            ),
            rationale="Some toolchains truncate long external names, silently merging distinct symbols.",
            tags=["linkage", "identifiers", "cross-tu"],
            references=["MISRA C:2012 Rule 5.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        if not linkage.data.get("symbols"):
            return []
        graph = self.graph(context)
        results: list[RuleResult] = []
        reported: set[frozenset[str]] = set()

        for first, second in linkage.duplicate_names_within(_SIGNIFICANT_CHARS):
            pair_key = frozenset((first, second))
            if pair_key in reported:
                continue
            local_decl = next(
                (
                    node
                    for node in graph.all_nodes()
                    if node.get("node_kind") in ("FunctionDecl", "VarDecl")
                    and node.get("semantic_properties", {}).get("name") in (first, second)
                ),
                None,
            )
            if local_decl is None:
                continue
            reported.add(pair_key)
            results.append(
                self.make_result(
                    context,
                    graph,
                    local_decl,
                    explanation=(
                        f"External identifiers '{first}' and '{second}' collide within the first "
                        f"{_SIGNIFICANT_CHARS} characters."
                    ),
                    risk_description="Truncating toolchains may link the wrong symbol without warning.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    confidence_score=0.78,
                    suggested_fix=SuggestedFix(
                        original_code=f"{first} / {second}",
                        suggested_code="rename one identifier so both are distinct within significant length",
                        rationale="Avoid relying on toolchain-specific significant-character limits.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["extern void initialize_temperature_sensor(void);"],
            non_compliant=[
                "extern void initialize_temperature_sensor_module_a(void);\n"
                "extern void initialize_temperature_sensor_module_b(void); /* colliding prefix */"
            ],
        )


class Rule8_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-7",
            rule_number="8.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="Functions/objects used in only one translation unit should have internal linkage",
            description="An externally-linked symbol referenced from a single translation unit should be static.",
            rationale="Unnecessary external linkage widens a symbol's visibility across the whole program.",
            tags=["linkage", "cross-tu"],
            references=["MISRA C:2012 Rule 8.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        if not linkage.data.get("symbols"):
            return []
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("FunctionDecl", "VarDecl"):
            for node in graph.nodes_by_kind(kind):
                if not graph.is_file_scope(node["node_id"]):
                    continue
                name = node.get("semantic_properties", {}).get("name", "")
                storage = node.get("semantic_properties", {}).get("storage_class", "external")
                if not name or storage == "static":
                    continue
                single_tu = linkage.single_translation_unit(name)
                if single_tu is None or single_tu != context.translation_unit_id:
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=f"'{name}' has external linkage but is only used in this translation unit.",
                        risk_description="Needless external linkage increases the whole-program symbol surface.",
                        confidence_factors={
                            "ast_match_specificity": 0.75,
                            "type_information_complete": 0.7,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.25,
                            "fix_generator_certainty": 0.55,
                        },
                        confidence_score=0.68,
                        suggested_fix=SuggestedFix(
                            original_code=f"{name}",
                            suggested_code=f"static {name}",
                            rationale="Give the symbol internal linkage since no other TU references it.",
                            confidence_score=0.55,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["static void helper(void) { /* only used in this file */ }"],
            non_compliant=["void helper(void) { /* only used in this file, but not static */ }"],
        )


class Rule8_10(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-10",
            rule_number="8.10",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="An inline function shall be declared with internal linkage",
            description="A function declared inline shall also be declared static.",
            rationale="An external-linkage inline function can be inconsistently inlined/defined across TUs.",
            tags=["linkage", "functions"],
            references=["MISRA C:2012 Rule 8.10"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.LINKAGE,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("FunctionDecl"):
            props = node.get("semantic_properties", {})
            if not props.get("is_inline", False):
                continue
            if props.get("storage_class", "external") == "static":
                continue
            name = props.get("name", "<anonymous>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Inline function '{name}' does not have internal (static) linkage.",
                    risk_description="Inconsistent inline definitions across TUs are undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.75,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=f"inline {name}",
                        suggested_code=f"static inline {name}",
                        rationale="Add the static keyword to inline function declarations.",
                        confidence_score=0.75,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["static inline uint16_t clamp(uint16_t v) { return v; }"],
            non_compliant=["inline uint16_t clamp(uint16_t v) { return v; }"],
        )


class Rule5_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-8",
            rule_number="5.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Identifiers that define objects/functions with external linkage shall be unique",
            description="Two distinct external-linkage entities shall not share the exact same identifier.",
            rationale="Reusing an external name for two distinct entities is a one-definition-rule risk.",
            tags=["linkage", "identifiers", "cross-tu"],
            references=["MISRA C:2012 Rule 5.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        if not linkage.data.get("symbols"):
            return []
        graph = self.graph(context)
        results: list[RuleResult] = []

        for name in linkage.all_names():
            if not linkage.has_multiple_definitions(name):
                continue
            local_decl = next(
                (
                    node
                    for node in graph.all_nodes()
                    if node.get("node_kind") in ("FunctionDecl", "VarDecl")
                    and node.get("semantic_properties", {}).get("name") == name
                ),
                None,
            )
            if local_decl is None:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    local_decl,
                    explanation=f"External identifier '{name}' defines more than one distinct entity across the project.",
                    risk_description="Sharing an external name across unrelated definitions risks a one-definition-rule violation.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.9,
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
            compliant=["/* a.c */\nuint16_t sensor_count;"],
            non_compliant=["/* a.c */\nuint16_t sensor_count = 0U;\n/* b.c */\nuint16_t sensor_count = 1U; /* unrelated definition, same name */"],
        )


class Rule5_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-9",
            rule_number="5.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="Identifiers that define objects/functions with internal linkage should be unique",
            description="A static (internal-linkage) identifier should not reuse a name used elsewhere in the project.",
            rationale="Reusing a static identifier's name across files is confusing during whole-program review.",
            tags=["linkage", "identifiers", "cross-tu"],
            references=["MISRA C:2012 Rule 5.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        if not linkage.data.get("symbols"):
            return []
        graph = self.graph(context)
        results: list[RuleResult] = []

        for name in linkage.all_names():
            internal_tus = linkage.internal_linkage_translation_units(name)
            if len(internal_tus) <= 1:
                continue
            if context.translation_unit_id not in internal_tus:
                continue
            local_decl = next(
                (
                    node
                    for node in graph.all_nodes()
                    if node.get("node_kind") in ("FunctionDecl", "VarDecl")
                    and node.get("semantic_properties", {}).get("name") == name
                    and node.get("semantic_properties", {}).get("storage_class") == "static"
                ),
                None,
            )
            if local_decl is None:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    local_decl,
                    explanation=f"Internal-linkage identifier '{name}' is reused in {len(internal_tus)} files.",
                    risk_description="Reusing a static identifier's name across files hinders whole-program review.",
                    confidence_factors={
                        "ast_match_specificity": 0.75,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.25,
                        "fix_generator_certainty": 0.35,
                    },
                    confidence_score=0.65,
                    suggested_fix=SuggestedFix(
                        original_code=name,
                        suggested_code=f"give each file's static '{name}' a distinct, more specific name",
                        rationale="Avoid reusing a static identifier's spelling across unrelated files.",
                        confidence_score=0.35,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["/* a.c */\nstatic void reset_state(void) { /* ... */ }"],
            non_compliant=[
                "/* a.c */\nstatic void handle(void) { /* module A */ }\n"
                "/* b.c */\nstatic void handle(void) { /* unrelated module B, same name */ }"
            ],
        )


class Rule8_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-5",
            rule_number="8.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="An external object or function shall be declared once in one and only one file",
            description="A non-defining declaration of an external object/function shall not be re-typed in more than one file.",
            rationale="Repeating a prototype in several files instead of a shared header risks silent drift.",
            tags=["linkage", "declarations", "cross-tu"],
            references=["MISRA C:2012 Rule 8.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        if not linkage.data.get("symbols"):
            return []
        graph = self.graph(context)
        results: list[RuleResult] = []

        for name in linkage.all_names():
            non_defining_tus = linkage.non_defining_external_translation_units(name)
            if len(non_defining_tus) <= 1:
                continue
            if context.translation_unit_id not in non_defining_tus:
                continue
            local_decl = next(
                (
                    node
                    for node in graph.all_nodes()
                    if node.get("node_kind") in ("FunctionDecl", "VarDecl")
                    and node.get("semantic_properties", {}).get("name") == name
                ),
                None,
            )
            if local_decl is None:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    local_decl,
                    explanation=(
                        f"'{name}' has a non-defining declaration repeated in "
                        f"{len(non_defining_tus)} different files instead of one shared header."
                    ),
                    risk_description="Duplicated hand-written prototypes can silently drift out of sync.",
                    confidence_factors={
                        "ast_match_specificity": 0.75,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.75,
                        "historical_false_positive_rate": 0.3,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.65,
                    suggested_fix=SuggestedFix(
                        original_code=f"declaration of {name}",
                        suggested_code=f"declare '{name}' once in a shared header and #include it everywhere",
                        rationale="Centralize the declaration instead of repeating it per file.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["/* shared.h, included by both a.c and b.c */\nextern uint16_t counter;"],
            non_compliant=[
                "/* a.c */\nextern uint16_t counter;\n/* b.c */\nextern uint16_t counter; /* re-typed, not shared via a header */"
            ],
        )


class Rule8_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-8",
            rule_number="8.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The static storage class specifier shall be used consistently",
            description="Every declaration of an internal-linkage identifier shall repeat the static specifier.",
            rationale="Omitting static on a later declaration of an already-internal-linkage identifier is confusing.",
            tags=["linkage", "declarations"],
            references=["MISRA C:2012 Rule 8.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.LINKAGE,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        results: list[RuleResult] = []

        for name in symbols.all_names():
            decls = [d for d in symbols.declarations(name) if d.get("node_kind") in ("FunctionDecl", "VarDecl")]
            if len(decls) < 2:
                continue
            storage_classes = {symbols.storage_class(d) for d in decls}
            if "static" not in storage_classes or len(storage_classes) <= 1:
                continue
            inconsistent = next(d for d in decls if symbols.storage_class(d) != "static")
            results.append(
                self.make_result(
                    context,
                    graph,
                    inconsistent,
                    explanation=f"'{name}' is declared 'static' elsewhere but not consistently on every declaration.",
                    risk_description="An inconsistent static specifier obscures the identifier's true (internal) linkage.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.6,
                    },
                    confidence_score=0.78,
                    suggested_fix=SuggestedFix(
                        original_code=name,
                        suggested_code=f"static {name}",
                        rationale="Repeat 'static' on every declaration of an internal-linkage identifier.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["static void helper(void);\nstatic void helper(void) { /* ... */ }"],
            non_compliant=["static void helper(void);\nvoid helper(void) { /* missing 'static' here */ }"],
        )


class Rule17_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-2",
            rule_number="17.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Functions shall not call themselves, directly or indirectly",
            description="Recursion (direct or indirect) shall not be used.",
            rationale="Recursion makes stack-depth analysis and worst-case timing unpredictable.",
            tags=["linkage", "functions", "recursion", "cross-tu"],
            references=["MISRA C:2012 Rule 17.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_linkage",
            requires_ast_nodes=["FunctionDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        linkage = self.linkage(context)
        in_cycles = set(linkage.functions_in_recursion_cycles())
        if not in_cycles:
            return []

        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("FunctionDecl"):
            name = node.get("semantic_properties", {}).get("name", "")
            if not name or name not in in_cycles:
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Function '{name}' participates in a recursion cycle.",
                    risk_description="Recursion makes stack-depth and timing analysis unpredictable.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.25,
                    },
                    confidence_score=0.8,
                    suggested_fix=SuggestedFix(
                        original_code=f"{name}",
                        suggested_code=f"replace recursive '{name}' with an iterative implementation",
                        rationale="Eliminate direct and indirect recursion.",
                        confidence_score=0.25,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint16_t factorial_iter(uint16_t n) {\n    uint16_t result = 1U;\n    while (n > 1U) {\n        result *= n--;\n    }\n    return result;\n}"],
            non_compliant=["uint16_t factorial(uint16_t n) {\n    if (n <= 1U) {\n        return 1U;\n    }\n    return n * factorial(n - 1U); /* recursion */\n}"],
        )
