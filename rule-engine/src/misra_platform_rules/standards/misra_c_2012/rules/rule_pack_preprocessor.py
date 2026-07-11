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


def _preprocessor_result(
    plugin: BaseRulePlugin,
    context: RuleContext,
    *,
    source_range: dict,
    offending_expression: str,
    explanation: str,
    risk_description: str,
    confidence_score: float = 0.85,
) -> RuleResult:
    return RuleResult(
        rule_id=plugin.metadata.rule_id,
        file_path=source_range.get("file_path", context.file_path),
        line_start=source_range.get("line_start", 0),
        line_end=source_range.get("line_end", 0),
        column_start=source_range.get("column_start", 0),
        column_end=source_range.get("column_end", 0),
        offending_expression=offending_expression,
        explanation=explanation,
        risk_description=risk_description,
        source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
        ast_node_id="",
        ast_node_path=[],
        confidence_score=confidence_score,
        confidence_factors={
            "ast_match_specificity": 0.85,
            "type_information_complete": 0.6,
            "macro_clarity": 0.9,
            "historical_false_positive_rate": 0.1,
            "fix_generator_certainty": 0.4,
        },
        suggested_fix=None,
    )


class Rule20_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-1",
            rule_number="20.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="#include directives should only be preceded by preprocessor directives or comments",
            description="#include shall not follow non-preprocessor source lines.",
            rationale="Code before an #include can be silently excluded when the header is reincluded.",
            tags=["preprocessor", "includes"],
            references=["MISRA C:2012 Rule 20.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for directive in macros.include_directives(context.macro_table):
            if not macros.include_preceded_by_non_preprocessor(directive):
                continue
            header = directive.get("header") or directive.get("included_file", "")
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=directive.get("range", {}),
                    offending_expression=f"#include {header}",
                    explanation="#include is preceded by non-preprocessor source.",
                    risk_description="Leading code can be excluded when the header is reincluded.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define APP 1\n#include \"app.h\""],
            non_compliant=["int32_t counter;\n#include \"app.h\""],
        )


class Rule20_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-2",
            rule_number="20.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Header names shall not contain ', \\, or comment sequences",
            description="A header name in #include shall not contain forbidden characters or comment starters.",
            rationale="Malformed header names produce implementation-defined behaviour.",
            tags=["preprocessor", "includes"],
            references=["MISRA C:2012 Rule 20.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for directive in macros.include_directives(context.macro_table):
            if not macros.include_has_invalid_header_chars(directive):
                continue
            header = directive.get("header") or directive.get("included_file", "")
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=directive.get("range", {}),
                    offending_expression=f"#include {header}",
                    explanation=f"Header name '{header}' contains forbidden characters.",
                    risk_description="Malformed header names are undefined behaviour.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#include <stdint.h>"],
            non_compliant=["#include \"bad//name.h\""],
        )


class Rule20_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-3",
            rule_number="20.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="#include directives shall use the correct syntax",
            description="#include shall use the <h> or \"h\" form only.",
            rationale="Malformed #include syntax is a hard preprocessing error.",
            tags=["preprocessor", "includes"],
            references=["MISRA C:2012 Rule 20.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for directive in macros.include_directives(context.macro_table):
            if not macros.include_has_invalid_syntax(directive):
                continue
            header = directive.get("header") or directive.get("included_file", "")
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=directive.get("range", {}),
                    offending_expression=f"#include {header}",
                    explanation="#include uses invalid syntax.",
                    risk_description="Malformed #include directives fail preprocessing.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#include \"app.h\""],
            non_compliant=["#include app.h /* missing quotes */"],
        )


class Rule20_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-6",
            rule_number="20.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Tokens introduced by # or ## shall be valid preprocessing tokens",
            description="Macro stringification/pasting shall produce valid preprocessing tokens.",
            rationale="Invalid pasted tokens break preprocessing in toolchain-specific ways.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.6"],
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
            if not macros.macro_has_invalid_preprocessor_tokens(macro_def):
                continue
            name = macro_def.get("name", "")
            source_range = macro_def.get("range", {})
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=source_range,
                    offending_expression=f"#define {name}",
                    explanation=f"Macro '{name}' pastes/stringifies invalid preprocessing tokens.",
                    risk_description="Invalid pasted tokens are undefined behaviour.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define JOIN(a, b) a##b"],
            non_compliant=["#define BAD(x) x## /* invalid paste */"],
        )


class Rule20_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-8",
            rule_number="20.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The controlling expression of #if/#elif shall evaluate to 0 or 1",
            description="A #if/#elif controlling expression shall be essentially Boolean.",
            rationale="Non-Boolean controlling expressions rely on implementation-defined truth rules.",
            tags=["preprocessor", "conditional-compilation"],
            references=["MISRA C:2012 Rule 20.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for branch in macros.conditional_branches(context.macro_table):
            if not macros.conditional_non_boolean_controlling_expression(branch):
                continue
            source_range = branch.get("range", {})
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=source_range,
                    offending_expression=f"#{branch.get('directive', 'if')} {branch.get('condition', '')}",
                    explanation="The controlling expression is not restricted to 0 or 1.",
                    risk_description="Non-Boolean #if expressions are implementation-defined.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#if (FEATURE == 1)"],
            non_compliant=["#if FEATURE /* not explicitly 0/1 */"],
        )


class Rule20_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-9",
            rule_number="20.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="All identifiers in a #if/#elif expression shall be #defined",
            description="Every identifier in a #if/#elif expression shall be defined before evaluation.",
            rationale="Undefined identifiers in #if expressions evaluate to 0, hiding configuration mistakes.",
            tags=["preprocessor", "conditional-compilation"],
            references=["MISRA C:2012 Rule 20.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for branch in macros.conditional_branches(context.macro_table):
            undefined = macros.conditional_undefined_identifiers(branch)
            if not undefined:
                continue
            source_range = branch.get("range", {})
            names = ", ".join(undefined)
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=source_range,
                    offending_expression=f"#{branch.get('directive', 'if')} {branch.get('condition', '')}",
                    explanation=f"#if/#elif expression uses undefined identifier(s): {names}.",
                    risk_description="Undefined identifiers silently evaluate to 0 in #if expressions.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#if defined(FEATURE_A)"],
            non_compliant=["#if (UNDEFINED_FLAG == 1)"],
        )


class Rule20_11(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-11",
            rule_number="20.11",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A macro parameter used with # shall not be followed by ##",
            description="A stringified macro parameter shall not be followed by an unparenthesized operator.",
            rationale="Stringification adjacent to operators produces fragile expansions.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.11"],
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
            if not macros.macro_stringify_param_unparenthesized_operator(macro_def):
                continue
            name = macro_def.get("name", "")
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=macro_def.get("range", {}),
                    offending_expression=f"#define {name}",
                    explanation=f"Macro '{name}' stringifies a parameter next to an unparenthesized operator.",
                    risk_description="Stringification next to operators is fragile and hard to review.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define STR(x) #x"],
            non_compliant=["#define BAD(x) #x + 1"],
        )


class Rule20_12(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-12",
            rule_number="20.12",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A macro parameter used with # shall not also be used with ##",
            description="A macro parameter shall not be both stringified and token-pasted.",
            rationale="Mixing # and ## on the same parameter is undefined behaviour.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.12"],
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
            if not macros.macro_param_mixed_stringify_and_paste(macro_def):
                continue
            name = macro_def.get("name", "")
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=macro_def.get("range", {}),
                    offending_expression=f"#define {name}",
                    explanation=f"Macro '{name}' uses # and ## on the same parameter.",
                    risk_description="Mixing stringification and token pasting is undefined behaviour.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define TOK(x) x"],
            non_compliant=["#define MIX(x) #x ## suffix"],
        )


class Rule20_13(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-13",
            rule_number="20.13",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="A line with a # directive shall have one of the permitted forms",
            description="Preprocessor directives shall match one of the permitted #directive forms.",
            rationale="Malformed # lines are preprocessing errors or silently ignored.",
            tags=["preprocessor", "directives"],
            references=["MISRA C:2012 Rule 20.13"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for directive in macros.preprocessor_directives(context.macro_table):
            if not macros.directive_has_invalid_form(directive):
                continue
            text = directive.get("text", directive.get("directive", "#"))
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=directive.get("range", {}),
                    offending_expression=text,
                    explanation="Preprocessor directive does not match a permitted form.",
                    risk_description="Malformed # directives break preprocessing.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define MAX 10"],
            non_compliant=["# unknown-directive"],
        )


class Rule20_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-5",
            rule_number="20.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="#undef should not be used",
            description="The #undef directive should not be used.",
            rationale="#undef makes macro visibility order-dependent and hard to audit.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for directive in macros.undef_directives(context.macro_table):
            name = directive.get("name", "<macro>")
            source_range = directive.get("range", {})
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=source_range,
                    offending_expression=f"#undef {name}",
                    explanation=f"#undef is used on macro '{name}'.",
                    risk_description="#undef makes macro visibility fragile and order-dependent.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define MAX_RETRIES 3"],
            non_compliant=["#define MAX_RETRIES 3\n#undef MAX_RETRIES"],
        )


class Rule20_10(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-20-10",
            rule_number="20.10",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The # and ## preprocessor operators should not be used",
            description="The stringification (#) and token-pasting (##) operators should not be used.",
            rationale="# and ## produce fragile expansions that are difficult to review.",
            tags=["preprocessor", "macros"],
            references=["MISRA C:2012 Rule 20.10"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_preprocessor",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        macros = self.macros()
        results: list[RuleResult] = []
        for macro_def in macros.macros_using_token_operators(context.macro_table):
            name = macro_def.get("name", "<macro>")
            operators = []
            if macro_def.get("uses_stringify"):
                operators.append("#")
            if macro_def.get("uses_token_paste"):
                operators.append("##")
            op_text = " and ".join(operators)
            source_range = macro_def.get("range", {})
            results.append(
                _preprocessor_result(
                    self,
                    context,
                    source_range=source_range,
                    offending_expression=f"#define {name} ... {op_text} ...",
                    explanation=f"Macro '{name}' uses the {op_text} preprocessor operator(s).",
                    risk_description="Stringification and token pasting are fragile and hard to review.",
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["#define LOG(msg) record(msg)"],
            non_compliant=["#define STR(x) #x\n#define JOIN(a,b) a##b"],
        )
