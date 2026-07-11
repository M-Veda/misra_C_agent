"""Standard library rule pack (Phase 6.2) — MISRA C:2012 Rules 17.1, 21.3–21.12,
21.21, 22.8. Header bans reuse `MacroAnalyzer`; call bans match
`CallExpr.semantic_properties.callee` against forbidden name sets."""

from misra_platform_rules.ast_graph import AstGraph
from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack

_STDIO_CALLS = frozenset({
    "clearerr", "fclose", "feof", "ferror", "fflush", "fgetc", "fgetpos", "fgets",
    "fopen", "fprintf", "fputc", "fputs", "fread", "freopen", "fscanf", "fseek",
    "fsetpos", "ftell", "fwrite", "getc", "getchar", "gets", "perror", "printf",
    "putc", "putchar", "puts", "remove", "rename", "rewind", "scanf", "setbuf",
    "setvbuf", "snprintf", "sprintf", "sscanf", "tmpfile", "tmpnam", "ungetc",
    "vfprintf", "vfscanf", "vprintf", "vscanf", "vsnprintf", "vsprintf", "vsscanf",
})

_ATO_CALLS = frozenset({"atof", "atoi", "atol", "atoll"})

_ABORT_EXIT_CALLS = frozenset({"abort", "exit", "getenv", "system"})

_MALLOC_CALLS = frozenset({"malloc", "calloc", "realloc", "free"})

_BSEARCH_QSORT_CALLS = frozenset({"bsearch", "qsort"})

_STDARG_CALLS = frozenset({"va_start", "va_arg", "va_end", "va_copy"})


def _forbidden_call_results(
    plugin: BaseRulePlugin,
    context: RuleContext,
    graph: AstGraph,
    forbidden: frozenset[str],
    *,
    explanation_template: str,
    risk_description: str,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    for node in graph.nodes_by_kind("CallExpr"):
        callee = node.get("semantic_properties", {}).get("callee", "")
        if callee not in forbidden:
            continue
        results.append(
            plugin.make_result(
                context,
                graph,
                node,
                explanation=explanation_template.format(callee=callee),
                risk_description=risk_description,
                confidence_factors={
                    "ast_match_specificity": 0.95,
                    "type_information_complete": 0.85,
                    "macro_clarity": 0.9,
                    "historical_false_positive_rate": 0.05,
                    "fix_generator_certainty": 0.4,
                },
                confidence_score=0.9,
                suggested_fix=SuggestedFix(
                    original_code=AstGraph.offending_text(node),
                    suggested_code="replace with a project-approved alternative",
                    rationale="Avoid banned standard-library facilities in safety-critical code.",
                    confidence_score=0.4,
                ),
            )
        )
    return results


def _forbidden_header_results(
    plugin: BaseRulePlugin,
    context: RuleContext,
    forbidden_headers: frozenset[str],
    *,
    explanation_template: str,
    risk_description: str,
) -> list[RuleResult]:
    macros = plugin.macros()
    results: list[RuleResult] = []
    for directive in macros.includes_matching(context.macro_table, forbidden_headers):
        header = directive.get("header") or directive.get("included_file", "")
        source_range = directive.get("range", {})
        results.append(
            RuleResult(
                rule_id=plugin.metadata.rule_id,
                file_path=source_range.get("file_path", context.file_path),
                line_start=source_range.get("line_start", 0),
                line_end=source_range.get("line_end", 0),
                column_start=source_range.get("column_start", 0),
                column_end=source_range.get("column_end", 0),
                offending_expression=f"#include {header}",
                explanation=explanation_template.format(header=header),
                risk_description=risk_description,
                source_snippet=f"{context.file_path}:{source_range.get('line_start', 0)}",
                ast_node_id="",
                ast_node_path=[],
                confidence_score=0.92,
                confidence_factors={
                    "ast_match_specificity": 0.95,
                    "type_information_complete": 0.7,
                    "macro_clarity": 0.95,
                    "historical_false_positive_rate": 0.05,
                    "fix_generator_certainty": 0.5,
                },
                suggested_fix=SuggestedFix(
                    original_code=f"#include {header}",
                    suggested_code="remove the include and use a project-approved alternative",
                    rationale="Banned standard-library headers shall not be included.",
                    confidence_score=0.5,
                ),
            )
        )
    return results


class Rule17_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-17-1",
            rule_number="17.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The features of <stdarg.h> shall not be used",
            description="The variable-argument facilities of <stdarg.h> shall not be used.",
            rationale="Variadic functions are difficult to verify and can violate type safety.",
            tags=["standard-library", "stdarg", "preprocessor"],
            references=["MISRA C:2012 Rule 17.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results = _forbidden_header_results(
            self,
            context,
            frozenset({"stdarg.h"}),
            explanation_template="Header '{header}' provides <stdarg.h> facilities that are banned.",
            risk_description="Variadic argument handling is difficult to verify in safety-critical code.",
        )
        results.extend(
            _forbidden_call_results(
                self,
                context,
                graph,
                _STDARG_CALLS,
                explanation_template="Call to variadic helper '{callee}' is banned.",
                risk_description="stdarg.h facilities shall not be used.",
            )
        )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["void log_fixed(int32_t code);"],
            non_compliant=["#include <stdarg.h>\nvoid log_variadic(const char *fmt, ...);"],
        )


class Rule21_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-3",
            rule_number="21.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The memory allocation/deallocation functions of <stdlib.h> shall not be used",
            description="malloc, calloc, realloc, and free shall not be used.",
            rationale="Dynamic memory allocation introduces unpredictable failure modes.",
            tags=["standard-library", "stdlib", "memory"],
            references=["MISRA C:2012 Rule 21.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            _MALLOC_CALLS,
            explanation_template="Call to dynamic-memory function '{callee}' is banned.",
            risk_description="Dynamic allocation is not permitted in this safety profile.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["static uint8_t buffer[64];"],
            non_compliant=["uint8_t *buffer = malloc(64U);"],
        )


class Rule21_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-4",
            rule_number="21.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The features of <setjmp.h> shall not be used",
            description="The setjmp/longjmp facilities shall not be used.",
            rationale="Non-local jumps break structured control flow and complicate verification.",
            tags=["standard-library", "setjmp", "preprocessor"],
            references=["MISRA C:2012 Rule 21.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_header_results(
            self,
            context,
            frozenset({"setjmp.h"}),
            explanation_template="Header '{header}' provides <setjmp.h> facilities that are banned.",
            risk_description="setjmp/longjmp shall not be used.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["/* no setjmp.h include */"],
            non_compliant=["#include <setjmp.h>"],
        )


class Rule21_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-5",
            rule_number="21.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The features of <signal.h> shall not be used",
            description="Signal-handling facilities shall not be used.",
            rationale="Asynchronous signal handlers introduce unpredictable control flow.",
            tags=["standard-library", "signal", "preprocessor"],
            references=["MISRA C:2012 Rule 21.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_header_results(
            self,
            context,
            frozenset({"signal.h"}),
            explanation_template="Header '{header}' provides <signal.h> facilities that are banned.",
            risk_description="Signal handling shall not be used.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["/* deterministic polling instead of signals */"],
            non_compliant=["#include <signal.h>"],
        )


class Rule21_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-6",
            rule_number="21.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The Standard Library input/output functions should not be used",
            description="stdio-style input/output functions should not be used.",
            rationale="stdio introduces host-environment dependencies and unpredictable blocking.",
            tags=["standard-library", "stdio"],
            references=["MISRA C:2012 Rule 21.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            _STDIO_CALLS,
            explanation_template="Call to stdio function '{callee}' is banned.",
            risk_description="Standard-library I/O should not be used in this safety profile.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uart_write(buffer, length);"],
            non_compliant=["printf(\"speed=%d\\n\", speed);"],
        )


class Rule21_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-7",
            rule_number="21.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The atof, atoi, atol and atoll functions shall not be used",
            description="The ato* string-to-number conversion functions shall not be used.",
            rationale="These functions provide no error reporting and have undefined overflow behaviour.",
            tags=["standard-library", "stdlib"],
            references=["MISRA C:2012 Rule 21.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            _ATO_CALLS,
            explanation_template="Call to banned conversion function '{callee}'.",
            risk_description="ato* functions provide no reliable error indication.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t value = parse_decimal(text, &ok);"],
            non_compliant=["int32_t value = atoi(text);"],
        )


class Rule21_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-8",
            rule_number="21.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The library functions abort, exit, getenv and system shall not be used",
            description="abort, exit, getenv, and system shall not be used.",
            rationale="These functions terminate or interact with the host environment unpredictably.",
            tags=["standard-library", "stdlib"],
            references=["MISRA C:2012 Rule 21.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            _ABORT_EXIT_CALLS,
            explanation_template="Call to banned environment/termination function '{callee}'.",
            risk_description="Process termination and host-environment calls are not permitted.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["safe_state_enter(SAFE_STATE_FAULT);"],
            non_compliant=["exit(1);"],
        )


class Rule21_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-9",
            rule_number="21.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The library functions bsearch and qsort should not be used",
            description="bsearch and qsort should not be used.",
            rationale="Comparator callbacks and runtime sorting complicate verification.",
            tags=["standard-library", "stdlib"],
            references=["MISRA C:2012 Rule 21.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            _BSEARCH_QSORT_CALLS,
            explanation_template="Call to banned sorting/search function '{callee}'.",
            risk_description="bsearch/qsort introduce callback-based control flow.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["insertion_sort(table, count);"],
            non_compliant=["qsort(table, count, sizeof(entry_t), compare_entries);"],
        )


class Rule21_10(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-10",
            rule_number="21.10",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The features of <time.h> should not be used",
            description="time.h facilities should not be used.",
            rationale="Wall-clock time is host-dependent and non-deterministic.",
            tags=["standard-library", "time", "preprocessor"],
            references=["MISRA C:2012 Rule 21.10"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_header_results(
            self,
            context,
            frozenset({"time.h"}),
            explanation_template="Header '{header}' provides <time.h> facilities that are banned.",
            risk_description="time.h should not be used in this safety profile.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint32_t ticks = os_get_tick_count();"],
            non_compliant=["#include <time.h>"],
        )


class Rule21_11(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-11",
            rule_number="21.11",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The features of <tgmath.h> should not be used",
            description="Type-generic math facilities should not be used.",
            rationale="tgmath.h relies on compiler magic and obscures essential types.",
            tags=["standard-library", "tgmath", "preprocessor"],
            references=["MISRA C:2012 Rule 21.11"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_header_results(
            self,
            context,
            frozenset({"tgmath.h"}),
            explanation_template="Header '{header}' provides <tgmath.h> facilities that are banned.",
            risk_description="Type-generic math should not be used.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["double angle = sin_rad(theta);"],
            non_compliant=["#include <tgmath.h>"],
        )


class Rule21_12(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-12",
            rule_number="21.12",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The exception-handling features of <fenv.h> should not be used",
            description="Floating-point environment control from <fenv.h> should not be used.",
            rationale="FENV manipulation is platform-specific and hard to verify.",
            tags=["standard-library", "fenv", "preprocessor"],
            references=["MISRA C:2012 Rule 21.12"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=[],
            implementation_category=RuleImplementationCategory.F_PREPROCESSOR,
            rule_pack=RulePack.PREPROCESSOR,
            requires_macro_expansion=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_header_results(
            self,
            context,
            frozenset({"fenv.h"}),
            explanation_template="Header '{header}' provides <fenv.h> facilities that are banned.",
            risk_description="Floating-point environment control should not be used.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["/* rely on compile-time FPU configuration */"],
            non_compliant=["#include <fenv.h>"],
        )


class Rule21_21(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-21",
            rule_number="21.21",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.CRITICAL,
            title="The system function of <stdlib.h> shall not be used",
            description="The system() function shall not be used.",
            rationale="system() invokes a host shell and is inherently non-deterministic.",
            tags=["standard-library", "stdlib"],
            references=["MISRA C:2012 Rule 21.21"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _forbidden_call_results(
            self,
            context,
            self.graph(context),
            frozenset({"system"}),
            explanation_template="Call to banned function '{callee}'.",
            risk_description="system() shall not be used.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["safe_state_enter(SAFE_STATE_FAULT);"],
            non_compliant=["system(\"reboot\");"],
        )


class Rule22_8(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-8",
            rule_number="22.8",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The value of errno shall be set to zero before calling an errno-setting function",
            description="errno shall be cleared before calling a function that may set it.",
            rationale="A stale errno value can be mistaken for a new error.",
            tags=["standard-library", "errno"],
            references=["MISRA C:2012 Rule 22.8"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.A_AST_ONLY,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("CallExpr"):
            props = node.get("semantic_properties", {})
            if not props.get("requires_errno_clear"):
                continue
            if props.get("errno_cleared"):
                continue
            callee = props.get("callee", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"errno was not cleared before calling '{callee}'.",
                    risk_description="A stale errno may be misread as belonging to this call.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="errno = 0; /* then call */",
                        rationale="Clear errno immediately before an errno-setting library call.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["errno = 0;\nvalue = strtol(text, NULL, 10);"],
            non_compliant=["value = strtol(text, NULL, 10); /* errno not cleared */"],
        )


class Rule21_14(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-14",
            rule_number="21.14",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The Standard Library function memcmp shall not be used to compare null terminated strings",
            description="memcmp shall not be used to compare null-terminated strings.",
            rationale="memcmp does not stop at the null terminator and may read past the string end.",
            tags=["standard-library", "strings", "memcmp"],
            references=["MISRA C:2012 Rule 21.14"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            props = node.get("semantic_properties", {})
            if props.get("callee") != "memcmp":
                continue
            if not props.get("compares_null_terminated_strings"):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="memcmp is used to compare null-terminated strings.",
                    risk_description="memcmp may read past the null terminator.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use strcmp instead of memcmp for null-terminated strings",
                        rationale="strcmp respects the null terminator.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t cmp = strcmp(a, b);"],
            non_compliant=["int32_t cmp = memcmp(a, b, strlen(a)); /* null-terminated strings */"],
        )


class Rule21_16(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-16",
            rule_number="21.16",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="Pointer arguments to memcmp should point to essentially signed, unsigned or char type",
            description=(
                "Pointer arguments to memcmp should point to a pointer, essentially signed char, "
                "unsigned char, or void type."
            ),
            rationale="memcmp on non-byte object types can compare padding bytes unpredictably.",
            tags=["standard-library", "memcmp", "pointers"],
            references=["MISRA C:2012 Rule 21.16"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            if node.get("semantic_properties", {}).get("callee") != "memcmp":
                continue
            for arg in graph.children(node["node_id"]):
                if not arg.get("semantic_properties", {}).get("invalid_pointer_argument"):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        arg,
                        explanation="memcmp argument has an inappropriate pointer essential type.",
                        risk_description="memcmp on non-byte types may compare padding bytes.",
                        confidence_factors={
                            "ast_match_specificity": 0.88,
                            "type_information_complete": 0.82,
                            "macro_clarity": 0.88,
                            "historical_false_positive_rate": 0.15,
                            "fix_generator_certainty": 0.35,
                        },
                        confidence_score=0.78,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(arg),
                            suggested_code="cast to uint8_t * or use a byte-oriented comparison",
                            rationale="memcmp arguments should be byte pointers.",
                            confidence_score=0.35,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t cmp = memcmp((const uint8_t *)a, (const uint8_t *)b, n);"],
            non_compliant=["int32_t cmp = memcmp(&struct_a, &struct_b, sizeof(struct_a));"],
        )


class Rule21_19(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-19",
            rule_number="21.19",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="Pointers returned by certain Standard Library functions shall only be used as if pointing to const-qualified type",
            description=(
                "Pointers returned by locale/string library functions shall be treated as "
                "pointer-to-const-qualified type."
            ),
            rationale="Library-returned pointers may point to read-only storage.",
            tags=["standard-library", "pointers", "qualifiers"],
            references=["MISRA C:2012 Rule 21.19"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["DeclRefExpr", "UnaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("DeclRefExpr", "UnaryOperator"):
            for node in graph.nodes_by_kind(kind):
                if not node.get("semantic_properties", {}).get("returned_pointer_missing_const"):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation="Library-returned pointer is used without const qualification.",
                        risk_description="Writing through a library-returned pointer may be undefined behaviour.",
                        confidence_factors={
                            "ast_match_specificity": 0.9,
                            "type_information_complete": 0.85,
                            "macro_clarity": 0.88,
                            "historical_false_positive_rate": 0.1,
                            "fix_generator_certainty": 0.5,
                        },
                        confidence_score=0.85,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="declare the pointer as const-qualified",
                            rationale="Treat library-returned pointers as read-only.",
                            confidence_score=0.5,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["const char *text = getenv(\"MODE\");"],
            non_compliant=["char *text = getenv(\"MODE\"); /* missing const */"],
        )


class Rule22_5(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-5",
            rule_number="22.5",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="A pointer to a FILE object shall not be dereferenced",
            description="The object addressed by a pointer to FILE shall not be accessed directly.",
            rationale="FILE objects are opaque; direct dereference is undefined behaviour.",
            tags=["standard-library", "stdio", "pointers"],
            references=["MISRA C:2012 Rule 22.5"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["UnaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        pointers = self.pointers()
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("UnaryOperator"):
            if node.get("semantic_properties", {}).get("opcode") != "*":
                continue
            children = graph.children(node["node_id"])
            if not children:
                continue
            if not pointers.is_file_pointer(children[0]):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="A FILE pointer is dereferenced directly.",
                    risk_description="FILE objects are opaque and shall not be accessed directly.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.88,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.05,
                        "fix_generator_certainty": 0.6,
                    },
                    confidence_score=0.9,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use stdio functions instead of dereferencing FILE*",
                        rationale="Never dereference a FILE pointer.",
                        confidence_score=0.6,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t ch = fgetc(stream);"],
            non_compliant=["FILE obj = *stream; /* dereference FILE* */"],
        )


class Rule22_7(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-7",
            rule_number="22.7",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The macro EOF shall only be compared with the unmodified return value of certain library functions",
            description="EOF shall only be compared with the unmodified return value of a stream input function.",
            rationale="Modifying the return value before comparing with EOF can miss end-of-file.",
            tags=["standard-library", "stdio", "eof"],
            references=["MISRA C:2012 Rule 22.7"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["BinaryOperator"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("BinaryOperator"):
            if not node.get("semantic_properties", {}).get("eof_operand_modified"):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="EOF is compared with a modified stream-input return value.",
                    risk_description="Modified return values may not equal EOF even at end-of-file.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.88,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="compare EOF with the unmodified return value",
                        rationale="Do not transform the stream-input result before EOF comparison.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["int32_t ch = fgetc(stream);\nif (ch == EOF) { /* ... */ }"],
            non_compliant=["if ((fgetc(stream) & 0xFF) == EOF) { /* modified before compare */ }"],
        )


class Rule22_1(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-1",
            rule_number="22.1",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="All resources obtained dynamically shall be explicitly released",
            description="Every dynamically obtained resource shall be explicitly deallocated.",
            rationale="Leaked dynamic resources exhaust memory and handles over time.",
            tags=["standard-library", "resources", "malloc"],
            references=["MISRA C:2012 Rule 22.1"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("CallExpr", "FunctionDecl"):
            for node in graph.nodes_by_kind(kind):
                if not node.get("semantic_properties", {}).get("dynamic_resource_leak"):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation="A dynamically obtained resource is not explicitly released.",
                        risk_description="Resource leaks accumulate and can exhaust system memory.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.15,
                            "fix_generator_certainty": 0.4,
                        },
                        confidence_score=0.78,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="add an explicit free/close for every dynamic allocation",
                            rationale="Pair every dynamic resource acquisition with an explicit release.",
                            confidence_score=0.4,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["uint8_t *buf = malloc(16U);\nif (buf != NULL) {\n    free(buf);\n}"],
            non_compliant=["uint8_t *buf = malloc(16U);\n/* never freed */"],
        )


class Rule22_2(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-2",
            rule_number="22.2",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="A resource obtained shall not be released more than once",
            description="A dynamically obtained resource shall not be freed or closed more than once.",
            rationale="Double release is undefined behaviour and corrupts heap bookkeeping.",
            tags=["standard-library", "resources", "free"],
            references=["MISRA C:2012 Rule 22.2"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            if not node.get("semantic_properties", {}).get("double_release"):
                continue
            callee = node.get("semantic_properties", {}).get("callee", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'{callee}' releases a resource that was already released.",
                    risk_description="Double release corrupts heap state and is undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="release the resource exactly once and null the pointer afterward",
                        rationale="Never call free/close on an already-released resource.",
                        confidence_score=0.45,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["free(buf);\nbuf = NULL;"],
            non_compliant=["free(buf);\nfree(buf); /* double release */"],
        )


class Rule22_3(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-3",
            rule_number="22.3",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.ADVISORY,
            severity=RuleSeverity.MINOR,
            title="The same file/stream should not be open for read and write at the same time in different streams",
            description="A file shall not be opened for read and write through different streams concurrently.",
            rationale="Concurrent read/write streams on one file invite data races and corruption.",
            tags=["standard-library", "stdio", "streams"],
            references=["MISRA C:2012 Rule 22.3"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.nodes_by_kind("CallExpr"):
            if not node.get("semantic_properties", {}).get("concurrent_stream_access"):
                continue
            callee = node.get("semantic_properties", {}).get("callee", "")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"'{callee}' opens concurrent read/write access to the same file.",
                    risk_description="Concurrent streams on one file can corrupt buffered I/O state.",
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.15,
                        "fix_generator_certainty": 0.35,
                    },
                    confidence_score=0.75,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="use a single stream or serialize access to the file",
                        rationale="Avoid opening the same file for read and write simultaneously.",
                        confidence_score=0.35,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["FILE *stream = fopen(\"data.txt\", \"r\");\n/* single stream only */"],
            non_compliant=["FILE *read = fopen(\"data.txt\", \"r\");\nFILE *write = fopen(\"data.txt\", \"w\");"],
        )


class Rule22_9(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-9",
            rule_number="22.9",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The value of errno shall be tested against zero after calling an errno-setting function",
            description="errno shall be tested after every call to a function that may set it.",
            rationale="Failing to test errno after an errno-setting call drops error information.",
            tags=["standard-library", "errno"],
            references=["MISRA C:2012 Rule 22.9"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "CompoundStmt"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for node in graph.all_nodes():
            if node.get("node_kind") not in ("CompoundStmt", "IfStmt", "WhileStmt", "ForStmt", "DoStmt"):
                continue
            if not node.get("semantic_properties", {}).get("errno_not_tested"):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation="errno was not tested after an errno-setting library call.",
                    risk_description="Untested errno may leave an error condition undetected.",
                    confidence_factors={
                        "ast_match_specificity": 0.88,
                        "type_information_complete": 0.8,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.12,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.82,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="if (errno != 0) { /* handle error */ }",
                        rationale="Test errno against zero after every errno-setting call.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["value = strtol(text, NULL, 10);\nif (errno != 0) { handle_error(); }"],
            non_compliant=["value = strtol(text, NULL, 10);\n/* errno not tested */"],
        )


class Rule22_10(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-10",
            rule_number="22.10",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="The value of errno shall only be tested when the function return value indicates failure",
            description="errno shall only be inspected when the preceding library call indicates failure.",
            rationale="errno is only meaningful when the return value shows the call failed.",
            tags=["standard-library", "errno"],
            references=["MISRA C:2012 Rule 22.10"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["BinaryOperator", "IfStmt"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []

        for kind in ("BinaryOperator", "IfStmt"):
            for node in graph.nodes_by_kind(kind):
                if not node.get("semantic_properties", {}).get("errno_tested_without_failure_check"):
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation="errno is tested without first checking that the library call failed.",
                        risk_description="errno may contain a stale value when the call succeeded.",
                        confidence_factors={
                            "ast_match_specificity": 0.88,
                            "type_information_complete": 0.8,
                            "macro_clarity": 0.85,
                            "historical_false_positive_rate": 0.12,
                            "fix_generator_certainty": 0.5,
                        },
                        confidence_score=0.82,
                        suggested_fix=SuggestedFix(
                            original_code=AstGraph.offending_text(node),
                            suggested_code="check the return value for failure before testing errno",
                            rationale="Only inspect errno when the function return indicates an error.",
                            confidence_score=0.5,
                        ),
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["value = strtol(text, NULL, 10);\nif ((value == 0) && (errno != 0)) { handle_error(); }"],
            non_compliant=["value = strtol(text, NULL, 10);\nif (errno != 0) { handle_error(); }"],
        )


def _alias_function_violations(
    plugin: BaseRulePlugin,
    context: RuleContext,
    graph: AstGraph,
    *,
    query: str,
    explanation: str,
    risk_description: str,
    suggested_fix: SuggestedFix | None = None,
) -> list[RuleResult]:
    results: list[RuleResult] = []
    for function_node in graph.nodes_by_kind("FunctionDecl"):
        if not any(
            child.get("node_kind") == "CompoundStmt" for child in graph.children(function_node["node_id"])
        ):
            continue
        aliases = plugin.aliases(function_node, graph, context)
        query_fn = getattr(aliases, query)
        for node in query_fn(function_node, graph):
            results.append(
                plugin.make_result(
                    context,
                    graph,
                    node,
                    explanation=explanation,
                    risk_description=risk_description,
                    confidence_factors={
                        "ast_match_specificity": 0.85,
                        "type_information_complete": 0.75,
                        "macro_clarity": 0.85,
                        "historical_false_positive_rate": 0.2,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.8,
                    suggested_fix=suggested_fix,
                )
            )
    return results


class Rule21_15(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-15",
            rule_number="21.15",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Pointer arguments to memcpy/memmove/memcmp shall be pointers to compatible types",
            description="Pointer arguments to memcpy, memmove, and memcmp shall point to compatible types.",
            rationale="Incompatible pointer types make the effective element size ambiguous.",
            tags=["standard-library", "aliasing", "memory"],
            references=["MISRA C:2012 Rule 21.15"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _alias_function_violations(
            self,
            context,
            self.graph(context),
            query="incompatible_mem_calls",
            explanation="memcpy/memmove/memcmp is called with incompatible pointer argument types.",
            risk_description="Incompatible pointer types make the memory operation's element size ambiguous.",
            suggested_fix=SuggestedFix(
                original_code="memcpy(...)",
                suggested_code="ensure both pointer arguments reference compatible object types",
                rationale="Use pointers to the same or compatible element types.",
                confidence_score=0.45,
            ),
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["memcpy(dest, src, n); /* uint8_t *dest, uint8_t *src */"],
            non_compliant=["memcpy(dest, src, n); /* uint8_t *dest, uint16_t *src */"],
        )


class Rule21_17(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-17",
            rule_number="21.17",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="String handling functions shall not cause overflow or underflow of the destination buffer",
            description="String-handling library functions shall not write past the destination buffer.",
            rationale="Buffer overflow from string functions is a common safety defect.",
            tags=["standard-library", "aliasing", "strings"],
            references=["MISRA C:2012 Rule 21.17"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _alias_function_violations(
            self,
            context,
            self.graph(context),
            query="string_buffer_overflow_calls",
            explanation="A string-handling function may overflow the destination buffer.",
            risk_description="Writing past the end of a string buffer is undefined behaviour.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["strncpy(dest, src, sizeof(dest) - 1U);"],
            non_compliant=["strcpy(dest, src); /* dest too small */"],
        )


class Rule21_18(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-18",
            rule_number="21.18",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="The size_t argument passed to a memory/string function shall not exceed the destination size",
            description="The size argument to a memory function shall not exceed the destination object size.",
            rationale="Copying more bytes than the destination can hold corrupts adjacent storage.",
            tags=["standard-library", "aliasing", "memory"],
            references=["MISRA C:2012 Rule 21.18"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _alias_function_violations(
            self,
            context,
            self.graph(context),
            query="size_exceeds_destination_calls",
            explanation="A memory function size argument exceeds the destination object size.",
            risk_description="Writing beyond the destination object corrupts adjacent storage.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["memcpy(dest, src, sizeof(dest));"],
            non_compliant=["memcpy(dest, src, sizeof(dest) + 1U);"],
        )


class Rule21_20(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-20",
            rule_number="21.20",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="A pointer to a string returned by a library function shall not be used after a subsequent call",
            description="Pointers to strings returned by certain library functions are invalidated by later calls.",
            rationale="Reusing an invalidated string pointer reads undefined storage.",
            tags=["standard-library", "aliasing", "strings"],
            references=["MISRA C:2012 Rule 21.20"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "DeclRefExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _alias_function_violations(
            self,
            context,
            self.graph(context),
            query="use_after_string_invalidation_reads",
            explanation="A string pointer is used after a subsequent library call invalidated it.",
            risk_description="Using an invalidated string pointer is undefined behaviour.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["token = strtok(buf, \",\");\nuse(token);"],
            non_compliant=["token = strtok(buf, \",\");\nstrtok(buf, \";\");\nuse(token);"],
        )


class Rule22_6(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-6",
            rule_number="22.6",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="The value of a pointer to a FILE shall not be used after the stream is closed",
            description="A FILE pointer shall not be dereferenced or passed to I/O functions after fclose.",
            rationale="Using a closed stream pointer is undefined behaviour.",
            tags=["standard-library", "aliasing", "stdio"],
            references=["MISRA C:2012 Rule 22.6"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr", "DeclRefExpr", "FunctionDecl"],
            implementation_category=RuleImplementationCategory.D_DATA_FLOW,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_dataflow=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return _alias_function_violations(
            self,
            context,
            self.graph(context),
            query="use_after_file_close_reads",
            explanation="A FILE pointer is used after the stream was closed.",
            risk_description="Using a FILE pointer after fclose is undefined behaviour.",
        )

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["fclose(stream);\nstream = fopen(path, \"r\");"],
            non_compliant=["fclose(stream);\nfprintf(stream, \"done\");"],
        )


_CTYPE_CALLS = frozenset({
    "isalnum", "isalpha", "isblank", "iscntrl", "isdigit", "isgraph", "islower",
    "isprint", "ispunct", "isspace", "isupper", "isxdigit", "tolower", "toupper",
})


class Rule21_13(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-21-13",
            rule_number="21.13",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="Any value passed to a <ctype.h> function shall be representable as unsigned char or EOF",
            description="Arguments to ctype.h functions shall be in [0, UCHAR_MAX] or EOF.",
            rationale="Passing a signed char with negative value to ctype functions is undefined behaviour.",
            tags=["standard-library", "ctype"],
            references=["MISRA C:2012 Rule 21.13"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("CallExpr"):
            props = node.get("semantic_properties", {})
            callee = props.get("callee", "")
            if callee not in _CTYPE_CALLS:
                continue
            if not props.get("argument_may_be_negative_char"):
                continue
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Argument to ctype function '{callee}' may be a negative char value.",
                    risk_description="ctype.h functions require unsigned char or EOF values.",
                    confidence_factors={
                        "ast_match_specificity": 0.9,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.1,
                        "fix_generator_certainty": 0.5,
                    },
                    confidence_score=0.85,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="cast the argument to unsigned char before the ctype call",
                        rationale="Ensure ctype arguments are representable as unsigned char or EOF.",
                        confidence_score=0.5,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["if (isalpha((unsigned char)ch)) { /* ... */ }"],
            non_compliant=["char ch = -1;\nif (isalpha(ch)) { /* UB */ }"],
        )


class Rule22_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-22-4",
            rule_number="22.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.MANDATORY,
            severity=RuleSeverity.CRITICAL,
            title="There shall be no attempt to write to a stream opened as read-only",
            description="A stream opened for reading shall not be written to.",
            rationale="Writing to a read-only stream is undefined behaviour.",
            tags=["standard-library", "stdio", "streams"],
            references=["MISRA C:2012 Rule 22.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_pack_standard_library",
            requires_ast_nodes=["CallExpr"],
            implementation_category=RuleImplementationCategory.B_TYPE_SYSTEM,
            rule_pack=RulePack.STANDARD_LIBRARY,
            requires_type_info=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        for node in graph.nodes_by_kind("CallExpr"):
            if not node.get("semantic_properties", {}).get("writes_to_readonly_stream"):
                continue
            callee = node.get("semantic_properties", {}).get("callee", "<call>")
            results.append(
                self.make_result(
                    context,
                    graph,
                    node,
                    explanation=f"Call to '{callee}' writes to a stream opened read-only.",
                    risk_description="Writing to a read-only stream is undefined behaviour.",
                    confidence_factors={
                        "ast_match_specificity": 0.92,
                        "type_information_complete": 0.85,
                        "macro_clarity": 0.9,
                        "historical_false_positive_rate": 0.08,
                        "fix_generator_certainty": 0.45,
                    },
                    confidence_score=0.88,
                    suggested_fix=SuggestedFix(
                        original_code=AstGraph.offending_text(node),
                        suggested_code="open the stream with a write-capable mode or use a separate output stream",
                        rationale="Only write to streams opened for writing.",
                        confidence_score=0.45,
                    ),
                )
            )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["FILE *out = fopen(\"log.txt\", \"w\");\nfprintf(out, \"ok\");"],
            non_compliant=["FILE *in = fopen(\"data.txt\", \"r\");\nfprintf(in, \"oops\");"],
        )
