"""Preprocessor rule pack (Phase 3/5) — MISRA C:2012 Rules 20.4, 20.7, 20.14,
21.1, 2.5, 5.4, 21.2. All detectors reuse `MacroAnalyzer` against the real
`PreprocessorMetadata` payload produced by clang-worker. Rule 21.2 also
reuses `SymbolIndex` to check *declared* identifiers, not just macros."""

from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_SIGNIFICANT_CHARS = 31  # ISO C99 minimum significant external-identifier length

_C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while", "_Bool", "_Complex", "_Imaginary",
}


class Rule20_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-4",
            rule_number="20.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A macro shall not be defined with the same name as a keyword",
            description="A macro shall not be #defined using a name that is a C language keyword.",
            rationale="Redefining a keyword via a macro is deeply confusing and toolchain-dependent.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for macro_def in macros.macro_definitions(context.macro_table):
            name = macro_def.get("name", "")
            if name not in _C_KEYWORDS:
                continue
            results.append(self._result(context, macro_def, name))
        return results

    def _result(self, context: RuleContext, macro_def: dict, name: str) -> RuleResult:
        source_range = macro_def.get("range", {})
        return RuleResult(
            rule_id=self.metadata.rule_id,
            file_path=source_range.get("file_path", context.file_path),
            line_start=source_range.get("line_start", 0),
            line_end=source_range.get("line_end", 0),
            column_start=source_range.get("column_start", 0),
            column_end=source_range.get("column_end", 0),
            offending_expression=f"#define {name}",
            explanation=f"Macro '{name}' shares its name with a C language keyword.",
            risk_description="Keyword-shadowing macros produce confusing, toolchain-dependent behaviour.",
            source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
            ast_node_id="",
            ast_node_path=[],
            confidence_score=0.9,
            confidence_factors={
                "ast_match_specificity": 0.9,
                "type_information_complete": 0.5,
                "macro_clarity": 0.95,
                "historical_false_positive_rate": 0.05,
                "fix_generator_certainty": 0.7,
            },
            suggested_fix=SuggestedFix(
                original_code=f"#define {name} ...",
                suggested_code=f"rename the macro away from the keyword '{name}'",
                rationale="Never shadow a language keyword with a macro.",
                confidence_score=0.7,
            ),
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define MAX_RETRIES 3"],
            non_compliant=["#define for while /* shadows the 'for' keyword */"],
        )


class Rule20_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-7",
            rule_number="20.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Expressions resulting from macro parameter substitution shall be parenthesized",
            description="A function-like macro body containing an operator shall wrap its expansion in parentheses.",
            rationale="Unparenthesized macro bodies are vulnerable to operator-precedence bugs at call sites.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for macro_def in macros.function_like_macros(context.macro_table):
            if not macros.has_unparenthesized_operator_body(macro_def):
                continue
            name = macro_def.get("name", "")
            source_range = macro_def.get("range", {})
            results.append(
                RuleResult(
                    rule_id=self.metadata.rule_id,
                    file_path=source_range.get("file_path", context.file_path),
                    line_start=source_range.get("line_start", 0),
                    line_end=source_range.get("line_end", 0),
                    column_start=source_range.get("column_start", 0),
                    column_end=source_range.get("column_end", 0),
                    offending_expression=f"#define {name}(...) {macro_def.get('value', '')}",
                    explanation=(
                        f"Function-like macro '{name}' has an unparenthesized operator in its body."
                    ),
                    risk_description="Operator precedence at the call site may change the intended meaning.",
                    source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
                    ast_node_id="",
                    ast_node_path=[],
                    confidence_score=0.65,
                    confidence_factors={
                        "ast_match_specificity": 0.6,
                        "type_information_complete": 0.4,
                        "macro_clarity": 0.6,
                        "historical_false_positive_rate": 0.3,
                        "fix_generator_certainty": 0.5,
                    },
                    suggested_fix=SuggestedFix(
                        original_code=macro_def.get("value", ""),
                        suggested_code=f"({macro_def.get('value', '')})",
                        rationale="Wrap the entire macro body in parentheses.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define SQUARE(x) ((x) * (x))"],
            non_compliant=["#define SQUARE(x) x * x"],
        )


class Rule20_14(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-14",
            rule_number="20.14",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="#if/#ifdef/#ifndef and matching #endif shall reside in the same file",
            description="All conditional-compilation groups shall be opened and closed within one file.",
            rationale="Splitting a conditional group across files makes inclusion order load-bearing and fragile.",
            tags=["preprocessor", "conditional-compilation"],
            references=["MISRA C:2012 Rule 20.14"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        if not macros.unbalanced_conditional_group(context.macro_table):
            return []
        branches = macros.conditional_branches(context.macro_table)
        first_range = branches[0].get("range", {}) if branches else {}
        return [
            RuleResult(
                rule_id=self.metadata.rule_id,
                file_path=first_range.get("file_path", context.file_path),
                line_start=first_range.get("line_start", 0),
                line_end=first_range.get("line_end", 0),
                column_start=first_range.get("column_start", 0),
                column_end=first_range.get("column_end", 0),
                offending_expression="#if/#ifdef/#ifndef .. #endif",
                explanation="This file contains an unbalanced set of conditional-compilation directives.",
                risk_description="An unmatched #if/#endif pair can silently exclude or include large code regions.",
                source_snippet=f"{context.file_path}:{first_range.get('line_start', 0)}",
                ast_node_id="",
                ast_node_path=[],
                confidence_score=0.75,
                confidence_factors={
                    "ast_match_specificity": 0.7,
                    "type_information_complete": 0.5,
                    "macro_clarity": 0.7,
                    "historical_false_positive_rate": 0.2,
                    "fix_generator_certainty": 0.3,
                },
                suggested_fix=None,
            )
        ]

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#ifdef FEATURE_X\n/* ... */\n#endif"],
            non_compliant=["#ifdef FEATURE_X\n/* ... endif in a different file ... */"],
        )


class Rule21_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-1",
            rule_number="21.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="#define and #undef shall not be used on a reserved identifier or reserved macro name",
            description="Macros shall not be defined using identifiers reserved by the C standard library.",
            rationale="Redefining reserved identifiers is undefined behaviour and can silently break the runtime.",
            tags=["preprocessor", "reserved-identifiers"],
            references=["MISRA C:2012 Rule 21.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for macro_def in macros.macro_definitions(context.macro_table):
            name = macro_def.get("name", "")
            if not name or not macros.is_reserved_identifier(name):
                continue
            source_range = macro_def.get("range", {})
            results.append(
                RuleResult(
                    rule_id=self.metadata.rule_id,
                    file_path=source_range.get("file_path", context.file_path),
                    line_start=source_range.get("line_start", 0),
                    line_end=source_range.get("line_end", 0),
                    column_start=source_range.get("column_start", 0),
                    column_end=source_range.get("column_end", 0),
                    offending_expression=f"#define {name}",
                    explanation=f"Macro name '{name}' is reserved by the C standard library.",
                    risk_description="Redefining a reserved identifier is undefined behaviour.",
                    source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
                    ast_node_id="",
                    ast_node_path=[],
                    confidence_score=0.92,
                    confidence_factors={
                        "ast_match_specificity": 0.95,
                        "type_information_complete": 0.6,
                        "macro_clarity": 0.95,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.6,
                    },
                    suggested_fix=SuggestedFix(
                        original_code=f"#define {name} ...",
                        suggested_code="rename to a non-reserved identifier (avoid leading underscore + uppercase)",
                        rationale="Reserve the leading-underscore namespace for the C library/implementation.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define APP_MAX_RETRIES 3"],
            non_compliant=["#define _MAX_RETRIES 3"],
        )


class Rule2_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-2-5",
            rule_number="2.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="A project should not contain unused macro declarations",
            description="Every #defined macro should be expanded somewhere in the project.",
            rationale="Unused macros are dead configuration surface that misleads future maintainers.",
            tags=["preprocessor", "macros", "unused"],
            references=["MISRA C:2012 Rule 2.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for macro_def in macros.macro_definitions(context.macro_table):
            if not macros.is_unused(context.macro_table, macro_def):
                continue
            name = macro_def.get("name", "")
            source_range = macro_def.get("range", {})
            results.append(
                RuleResult(
                    rule_id=self.metadata.rule_id,
                    file_path=source_range.get("file_path", context.file_path),
                    line_start=source_range.get("line_start", 0),
                    line_end=source_range.get("line_end", 0),
                    column_start=source_range.get("column_start", 0),
                    column_end=source_range.get("column_end", 0),
                    offending_expression=f"#define {name}",
                    explanation=f"Macro '{name}' is defined but never expanded anywhere in this translation unit.",
                    risk_description="Unused macros are dead configuration surface that misleads maintainers.",
                    source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
                    ast_node_id="",
                    ast_node_path=[],
                    confidence_score=0.6,
                    confidence_factors={
                        "ast_match_specificity": 0.6,
                        "type_information_complete": 0.4,
                        "macro_clarity": 0.65,
                        "historical_false_positive_rate": 0.35,
                        "fix_generator_certainty": 0.4,
                    },
                    suggested_fix=SuggestedFix(
                        original_code=f"#define {name} ...",
                        suggested_code="remove the unused macro, or expand it where intended",
                        rationale="Delete dead macro declarations once they are no longer expanded.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define BUFFER_SIZE 64\nuint8_t buffer[BUFFER_SIZE];"],
            non_compliant=["#define BUFFER_SIZE 64 /* never expanded anywhere */"],
        )


class Rule5_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-5-4",
            rule_number="5.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Macro identifiers shall be distinct",
            description=(
                f"Macro identifiers shall be distinct within the first {_SIGNIFICANT_CHARS} "
                "significant characters."
            ),
            rationale="Truncating preprocessors may silently merge two intended-distinct macro names.",
            tags=["preprocessor", "macros", "identifiers"],
            references=["MISRA C:2012 Rule 5.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        by_name = {m.get("name", ""): m for m in macros.macro_definitions(context.macro_table)}
        reported: set[frozenset[str]] = set()

        for first, second in macros.duplicate_macro_names_within(context.macro_table, _SIGNIFICANT_CHARS):
            key = frozenset((first, second))
            if key in reported:
                continue
            reported.add(key)
            macro_def = by_name.get(second) or by_name.get(first)
            if macro_def is None:
                continue
            source_range = macro_def.get("range", {})
            results.append(
                RuleResult(
                    rule_id=self.metadata.rule_id,
                    file_path=source_range.get("file_path", context.file_path),
                    line_start=source_range.get("line_start", 0),
                    line_end=source_range.get("line_end", 0),
                    column_start=source_range.get("column_start", 0),
                    column_end=source_range.get("column_end", 0),
                    offending_expression=f"#define {first} / #define {second}",
                    explanation=(
                        f"Macro identifiers '{first}' and '{second}' collide within the first "
                        f"{_SIGNIFICANT_CHARS} characters."
                    ),
                    risk_description="A truncating preprocessor may treat these two macros as the same identifier.",
                    source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
                    ast_node_id="",
                    ast_node_path=[],
                    confidence_score=0.78,
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.7,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.4,
                    },
                    suggested_fix=SuggestedFix(
                        original_code=f"{first} / {second}",
                        suggested_code="rename one macro so both are distinct within significant length",
                        rationale="Avoid relying on toolchain-specific significant-character limits.",
                        confidence_score=0.4,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define SENSOR_TIMEOUT_MS 100"],
            non_compliant=[
                "#define SENSOR_TIMEOUT_THRESHOLD_MODULE_A 100\n"
                "#define SENSOR_TIMEOUT_THRESHOLD_MODULE_B 200 /* colliding prefix */"
            ],
        )


class Rule21_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-2",
            rule_number="21.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A reserved identifier shall not be declared",
            description="No declared identifier (object, function, typedef, tag) shall use a name reserved by the C standard library.",
            rationale="Declaring a reserved identifier is undefined behaviour and can silently clash with the runtime.",
            tags=["preprocessor", "reserved-identifiers", "declarations"],
            references=["MISRA C:2012 Rule 21.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=["VarDecl", "FunctionDecl", "TypedefDecl", "RecordDecl", "EnumDecl"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.PREPROCESSOR,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        symbols = self.symbols(graph, context)
        macros = self.macros()
        results: list[RuleResult] = []

        for name in symbols.all_names():
            if not macros.is_reserved_identifier(name):
                continue
            for node in symbols.declarations(name):
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=f"Declared identifier '{name}' is reserved by the C standard library.",
                        risk_description="Declaring a reserved identifier is undefined behaviour.",
                        confidence_factors={
                            "ast_match_specificity": 0.95,
                            "type_information_complete": 0.8,
                            "macro_clarity": 0.95,
                            "historical_false_positive_rate": 0.05,
                            "fix_generator_certainty": 0.6,
                        },
                        confidence_score=0.9,
                        suggested_fix=SuggestedFix(
                            original_code=name,
                            suggested_code="rename to a non-reserved identifier (avoid leading underscore + uppercase)",
                            rationale="Reserve the leading-underscore namespace for the C library/implementation.",
                            confidence_score=0.6,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t retry_count;"],
            non_compliant=["int32_t _RetryCount; /* reserved: leading underscore + uppercase */"],
        )
