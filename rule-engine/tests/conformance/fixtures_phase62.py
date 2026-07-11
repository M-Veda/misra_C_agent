"""Phase 6.2 conformance fixtures — five case kinds per AST-only ready_now rule."""

from conformance.ast_builders import Builder
from misra_platform_rules.conformance import ConformanceCase, RuleConformanceSuite


def _suite(rule_id: str, cases: list[ConformanceCase]) -> RuleConformanceSuite:
    return RuleConformanceSuite(rule_id=rule_id, cases=cases)


def _five(
    rule_id: str,
    positive: dict,
    negative: dict,
    macro: dict | None = None,
    embedded: dict | None = None,
    edge: dict | None = None,
) -> RuleConformanceSuite:
    return _suite(
        rule_id,
        [
            ConformanceCase("pos-1", "positive", positive, True),
            ConformanceCase("neg-1", "negative", negative, False),
            ConformanceCase("macro-1", "macro", macro or positive, True),
            ConformanceCase("embedded-1", "embedded", embedded or positive, True),
            ConformanceCase("edge-1", "edge", edge or negative, False),
        ],
    )


def rule_2_6() -> RuleConformanceSuite:
    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = compliant.node("CompoundStmt", parent=fn)
    compliant.node("GotoStmt", parent=body, semantic_properties={"target_label": "done"})
    compliant.node("LabelStmt", parent=body, semantic_properties={"name": "done"})

    non_compliant = Builder()
    fn2 = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = non_compliant.node("CompoundStmt", parent=fn2)
    non_compliant.node("LabelStmt", parent=body2, semantic_properties={"name": "orphan"})

    macro = Builder()
    fn3 = macro.node("FunctionDecl", semantic_properties={"name": "f"})
    body3 = macro.node("CompoundStmt", parent=fn3)
    macro.node("LabelStmt", parent=body3, semantic_properties={"name": "unused"}, macro_origin={"macro_name": "LABEL"})

    embedded = Builder()
    fn4 = embedded.node("FunctionDecl", semantic_properties={"name": "HAL_Reset"})
    body4 = embedded.node("CompoundStmt", parent=fn4)
    embedded.node("LabelStmt", parent=body4, semantic_properties={"name": "retry"})

    return _five(
        "misra-c2012-rule-2-6",
        non_compliant.artifact(),
        compliant.artifact(),
        macro.artifact(),
        embedded.artifact(),
        Builder().artifact(),
    )


def rule_13_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    assign = non_compliant.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    non_compliant.node("ArraySubscriptExpr", parent=assign)
    non_compliant.node("UnaryOperator", parent=assign, semantic_properties={"opcode": "++"})

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node("UnaryOperator", parent=body2, semantic_properties={"opcode": "++"})

    macro = Builder()
    fn3 = macro.node("FunctionDecl", semantic_properties={"name": "f"})
    body3 = macro.node("CompoundStmt", parent=fn3)
    call = macro.node("CallExpr", parent=body3, semantic_properties={"callee": "LOG"})
    macro.node("UnaryOperator", parent=call, semantic_properties={"opcode": "++"}, macro_origin={"macro_name": "INC"})

    embedded = Builder()
    fn4 = embedded.node("FunctionDecl", semantic_properties={"name": "store"})
    body4 = embedded.node("CompoundStmt", parent=fn4)
    assign4 = embedded.node("BinaryOperator", parent=body4, semantic_properties={"opcode": "="})
    embedded.node("DeclRefExpr", parent=assign4, semantic_properties={"name": "buffer"})
    embedded.node("UnaryOperator", parent=assign4, semantic_properties={"opcode": "--"})

    edge = Builder()
    fn5 = edge.node("FunctionDecl", semantic_properties={"name": "f"})
    body5 = edge.node("CompoundStmt", parent=fn5)
    edge.node("ReturnStmt", parent=body5)

    return _five(
        "misra-c2012-rule-13-3",
        non_compliant.artifact(),
        compliant.artifact(),
        macro.artifact(),
        embedded.artifact(),
        edge.artifact(),
    )


def rule_17_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "refresh_cache", "has_non_void_return": True},
    )

    compliant_void = Builder()
    fn2 = compliant_void.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant_void.node("CompoundStmt", parent=fn2)
    cast_parent = compliant_void.node("CStyleCastExpr", parent=body2, semantic_properties={"cast_to_void": True})
    compliant_void.node(
        "CallExpr",
        parent=cast_parent,
        semantic_properties={"callee": "refresh_cache", "has_non_void_return": True},
    )

    macro = Builder()
    fn3 = macro.node("FunctionDecl", semantic_properties={"name": "f"})
    body3 = macro.node("CompoundStmt", parent=fn3)
    macro.node(
        "CallExpr",
        parent=body3,
        semantic_properties={"callee": "refresh_cache", "has_non_void_return": True},
        macro_origin={"macro_name": "REFRESH"},
    )

    embedded = Builder()
    fn4 = embedded.node("FunctionDecl", semantic_properties={"name": "adc_init"})
    body4 = embedded.node("CompoundStmt", parent=fn4)
    embedded.node(
        "CallExpr",
        parent=body4,
        semantic_properties={"callee": "HAL_ADC_Init", "has_non_void_return": True},
    )

    edge = Builder()
    fn5 = edge.node("FunctionDecl", semantic_properties={"name": "f"})
    body5 = edge.node("CompoundStmt", parent=fn5)
    edge.node("CallExpr", parent=body5, semantic_properties={"callee": "noop", "has_non_void_return": False})

    return _five(
        "misra-c2012-rule-17-7",
        non_compliant.artifact(),
        compliant_void.artifact(),
        macro.artifact(),
        embedded.artifact(),
        edge.artifact(),
    )


def rule_17_1() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-17-1",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"included_file": "<stdarg.h>", "range": {}}]},
        },
        {"file_path": "demo.c", "nodes": [], "diagnostics": [], "preprocessor": {}},
        {
            "file_path": "demo.c",
            "nodes": [{"node_id": "c1", "node_kind": "CallExpr", "parent_id": "", "children_ids": [],
                       "semantic_properties": {"callee": "va_start"}, "source_range": {"line_start": 3}}],
            "diagnostics": [],
            "preprocessor": {},
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"header": "stdarg.h", "range": {}}]},
        },
        {"file_path": "demo.c", "nodes": [], "diagnostics": [], "preprocessor": {"include_directives": []}},
    )


def _header_rule(rule_id: str, header: str) -> RuleConformanceSuite:
    return _five(
        rule_id,
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"included_file": f"<{header}>", "range": {}}]},
        },
        {"file_path": "demo.c", "nodes": [], "diagnostics": [], "preprocessor": {}},
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"included_file": f'"{header}"', "range": {}}]},
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"header": header, "range": {}}]},
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {"include_directives": [{"included_file": "<stdint.h>", "range": {}}]},
        },
    )


def rule_21_4() -> RuleConformanceSuite:
    return _header_rule("misra-c2012-rule-21-4", "setjmp.h")


def rule_21_5() -> RuleConformanceSuite:
    return _header_rule("misra-c2012-rule-21-5", "signal.h")


def rule_21_10() -> RuleConformanceSuite:
    return _header_rule("misra-c2012-rule-21-10", "time.h")


def rule_21_11() -> RuleConformanceSuite:
    return _header_rule("misra-c2012-rule-21-11", "tgmath.h")


def rule_21_12() -> RuleConformanceSuite:
    return _header_rule("misra-c2012-rule-21-12", "fenv.h")


def _call_rule(rule_id: str, callee: str, compliant_callee: str = "app_init") -> RuleConformanceSuite:
    def _artifact(name: str, macro: bool = False) -> dict:
        b = Builder()
        fn = b.node("FunctionDecl", semantic_properties={"name": "f"})
        body = b.node("CompoundStmt", parent=fn)
        props = {"callee": name}
        kwargs = {"macro_origin": {"macro_name": "CALL"}} if macro else {}
        b.node("CallExpr", parent=body, semantic_properties=props, **kwargs)
        return b.artifact()

    return _five(
        rule_id,
        _artifact(callee),
        _artifact(compliant_callee),
        _artifact(callee, macro=True),
        _artifact(callee),
        {"file_path": "demo.c", "nodes": [], "diagnostics": [], "preprocessor": {}},
    )


def rule_21_3() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-3", "malloc")


def rule_21_6() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-6", "printf")


def rule_21_7() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-7", "atoi")


def rule_21_8() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-8", "exit")


def rule_21_9() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-9", "qsort")


def rule_21_21() -> RuleConformanceSuite:
    return _call_rule("misra-c2012-rule-21-21", "system")


def rule_22_8() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "strtol", "requires_errno_clear": True, "errno_cleared": False},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "CallExpr",
        parent=body2,
        semantic_properties={"callee": "strtol", "requires_errno_clear": True, "errno_cleared": True},
    )

    macro = Builder()
    fn3 = macro.node("FunctionDecl", semantic_properties={"name": "f"})
    body3 = macro.node("CompoundStmt", parent=fn3)
    macro.node(
        "CallExpr",
        parent=body3,
        semantic_properties={"callee": "strtol", "requires_errno_clear": True, "errno_cleared": False},
        macro_origin={"macro_name": "PARSE"},
    )

    embedded = Builder()
    fn4 = embedded.node("FunctionDecl", semantic_properties={"name": "parse_adc"})
    body4 = embedded.node("CompoundStmt", parent=fn4)
    embedded.node(
        "CallExpr",
        parent=body4,
        semantic_properties={"callee": "strtod", "requires_errno_clear": True, "errno_cleared": False},
    )

    edge = Builder()
    fn5 = edge.node("FunctionDecl", semantic_properties={"name": "f"})
    body5 = edge.node("CompoundStmt", parent=fn5)
    edge.node("CallExpr", parent=body5, semantic_properties={"callee": "memcpy"})

    return _five(
        "misra-c2012-rule-22-8",
        non_compliant.artifact(),
        compliant.artifact(),
        macro.artifact(),
        embedded.artifact(),
        edge.artifact(),
    )


def rule_20_1() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-1",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "\"app.h\"", "preceded_by_non_preprocessor": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "\"app.h\"", "preceded_by_non_preprocessor": False, "range": {}}]
            },
        },
    )


def rule_20_2() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-2",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "\"bad//name.h\"", "invalid_header_chars": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "<stdint.h>", "range": {}}]
            },
        },
    )


def rule_20_3() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-3",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "app.h", "invalid_syntax": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "include_directives": [{"included_file": "\"app.h\"", "range": {}}]
            },
        },
    )


def rule_20_6() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-6",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [{"name": "BAD", "invalid_preprocessor_tokens": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [{"name": "JOIN", "value": "a##b", "range": {}}]
            },
        },
    )


def rule_20_8() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-8",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "conditional_branches": [
                    {"directive": "if", "condition": "FEATURE", "non_boolean_controlling_expression": True, "range": {}}
                ]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "conditional_branches": [
                    {"directive": "if", "condition": "(FEATURE == 1)", "range": {}},
                    {"directive": "endif", "range": {}},
                ]
            },
        },
    )


def rule_20_9() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-9",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "conditional_branches": [
                    {
                        "directive": "if",
                        "condition": "UNDEFINED_FLAG",
                        "undefined_identifiers": ["UNDEFINED_FLAG"],
                        "range": {},
                    }
                ]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "conditional_branches": [{"directive": "ifdef", "condition": "FEATURE_A", "range": {}}]
            },
        },
    )


def rule_20_11() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-11",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [
                    {"name": "BAD", "stringify_param_unparenthesized_operator": True, "range": {}}
                ]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [{"name": "STR", "value": "#x", "is_function_like": True, "range": {}}]
            },
        },
    )


def rule_20_12() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-12",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [{"name": "MIX", "param_mixed_stringify_and_paste": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "macro_definitions": [{"name": "TOK", "value": "x", "is_function_like": True, "range": {}}]
            },
        },
    )


def rule_20_13() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-20-13",
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "preprocessor_directives": [{"text": "# unknown", "invalid_form": True, "range": {}}]
            },
        },
        {
            "file_path": "demo.c",
            "nodes": [],
            "diagnostics": [],
            "preprocessor": {
                "preprocessor_directives": [{"text": "#define MAX 10", "range": {}}]
            },
        },
    )


PHASE62_SUITE_BUILDERS = [
    rule_2_6,
    rule_13_3,
    rule_17_1,
    rule_17_7,
    rule_20_1,
    rule_20_2,
    rule_20_3,
    rule_20_6,
    rule_20_8,
    rule_20_9,
    rule_20_11,
    rule_20_12,
    rule_20_13,
    rule_21_3,
    rule_21_4,
    rule_21_5,
    rule_21_6,
    rule_21_7,
    rule_21_8,
    rule_21_9,
    rule_21_10,
    rule_21_11,
    rule_21_12,
    rule_21_21,
    rule_22_8,
]
