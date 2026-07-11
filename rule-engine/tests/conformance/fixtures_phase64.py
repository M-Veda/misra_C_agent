"""Phase 6.4 conformance fixtures — five case kinds per CFG/Dataflow/Linkage ready_now rule."""

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
    *,
    positive_linkage: dict | None = None,
    negative_linkage: dict | None = None,
    macro_linkage: dict | None = None,
    embedded_linkage: dict | None = None,
    edge_linkage: dict | None = None,
) -> RuleConformanceSuite:
    return _suite(
        rule_id,
        [
            ConformanceCase("pos-1", "positive", positive, True, cross_tu_linkage=positive_linkage),
            ConformanceCase("neg-1", "negative", negative, False, cross_tu_linkage=negative_linkage),
            ConformanceCase("macro-1", "macro", macro or positive, True, cross_tu_linkage=macro_linkage),
            ConformanceCase(
                "embedded-1", "embedded", embedded or positive, True, cross_tu_linkage=embedded_linkage
            ),
            ConformanceCase("edge-1", "edge", edge or negative, False, cross_tu_linkage=edge_linkage),
        ],
    )


def _param_modify_fixture() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "process"})
    body = b.node("CompoundStmt", parent=fn)
    b.node("ParmVarDecl", parent=fn, semantic_properties={"name": "value"})
    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=assign, semantic_properties={"name": "value"})
    b.node("IntegerLiteral", parent=assign, semantic_properties={"value": "1"})
    return b.artifact()


def _param_no_modify_fixture() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "process"})
    body = b.node("CompoundStmt", parent=fn)
    b.node("ParmVarDecl", parent=fn, semantic_properties={"name": "value"})
    local = b.node("VarDecl", parent=body, semantic_properties={"name": "local"})
    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=assign, semantic_properties={"name": "local"})
    b.node("DeclRefExpr", parent=assign, semantic_properties={"name": "value"})
    return b.artifact()


def rule_16_1() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("SwitchStmt", semantic_properties={"switch_malformed": True})

    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = compliant.node("CompoundStmt", parent=fn)
    switch = compliant.node("SwitchStmt", parent=body)
    compliant.node("DeclRefExpr", parent=switch)
    switch_body = compliant.node("CompoundStmt", parent=switch)
    compliant.node("CaseStmt", parent=switch_body, semantic_properties={"value": "1"})

    return _five(
        "misra-c2012-rule-16-1",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_14_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("IfStmt", semantic_properties={"controlling_expression_invariant": True})

    compliant = Builder()
    compliant.node("IfStmt")

    return _five(
        "misra-c2012-rule-14-3",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_1_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "BinaryOperator",
        semantic_properties={"opcode": "<<", "undefined_behaviour": True},
    )

    compliant = Builder()
    compliant.node("BinaryOperator", semantic_properties={"opcode": "+"})

    return _five(
        "misra-c2012-rule-1-3",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_13_2() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "BinaryOperator",
        semantic_properties={"opcode": "=", "unordered_evaluation": True},
    )

    compliant = Builder()
    compliant.node("BinaryOperator", semantic_properties={"opcode": "+"})

    return _five(
        "misra-c2012-rule-13-2",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_17_8() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-17-8",
        _param_modify_fixture(),
        _param_no_modify_fixture(),
    )


def rule_8_13() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "ParmVarDecl",
        semantic_properties={"name": "buffer", "pointer_should_be_const": True},
        type_information={"is_pointer": True, "spelling": "uint8_t *"},
    )

    compliant = Builder()
    compliant.node(
        "ParmVarDecl",
        semantic_properties={"name": "buffer"},
        qualifiers=["const"],
        type_information={"is_pointer": True, "spelling": "const uint8_t *"},
    )

    return _five(
        "misra-c2012-rule-8-13",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_1() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "CallExpr",
        semantic_properties={"callee": "malloc", "dynamic_resource_leak": True},
    )

    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = compliant.node("CompoundStmt", parent=fn)
    compliant.node("CallExpr", parent=body, semantic_properties={"callee": "malloc"})
    compliant.node("CallExpr", parent=body, semantic_properties={"callee": "free"})

    embedded = Builder()
    embedded_fn = embedded.node("FunctionDecl", semantic_properties={"name": "HAL_Alloc", "dynamic_resource_leak": True})
    embedded.node("CompoundStmt", parent=embedded_fn)

    return _five(
        "misra-c2012-rule-22-1",
        non_compliant.artifact(),
        compliant.artifact(),
        embedded=embedded.artifact(),
    )


def rule_22_2() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "CallExpr",
        semantic_properties={"callee": "free", "double_release": True},
    )

    compliant = Builder()
    compliant.node("CallExpr", semantic_properties={"callee": "free"})

    return _five(
        "misra-c2012-rule-22-2",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "CallExpr",
        semantic_properties={"callee": "fopen", "concurrent_stream_access": True},
    )

    compliant = Builder()
    compliant.node("CallExpr", semantic_properties={"callee": "fopen"})

    return _five(
        "misra-c2012-rule-22-3",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_9() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("CompoundStmt", semantic_properties={"errno_not_tested": True})

    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = compliant.node("CompoundStmt", parent=fn)
    compliant.node("CallExpr", parent=body, semantic_properties={"callee": "strtol"})
    if_stmt = compliant.node("IfStmt", parent=body)
    compliant.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "!="})

    return _five(
        "misra-c2012-rule-22-9",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_10() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("IfStmt", semantic_properties={"errno_tested_without_failure_check": True})

    compliant = Builder()
    compliant.node("IfStmt")

    return _five(
        "misra-c2012-rule-22-10",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_17_2() -> RuleConformanceSuite:
    cycle_linkage = {"symbols": {}, "call_graph": {"fact": ["fact"], "helper": ["fact"]}}
    no_cycle_linkage = {"symbols": {}, "call_graph": {"helper": ["other"]}}
    empty_linkage = {"symbols": {}, "call_graph": {}}

    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "fact"})

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "helper"})

    b3 = Builder()
    b3.node(
        "FunctionDecl",
        semantic_properties={"name": "fact"},
        macro_origin={"macro_name": "RECURSIVE_FN"},
    )

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "ADC_Process"})

    b5 = Builder()
    b5.node("FunctionDecl", semantic_properties={"name": "linear"})

    return _five(
        "misra-c2012-rule-17-2",
        b1.artifact(),
        b2.artifact(),
        macro=b3.artifact(),
        embedded=b4.artifact(),
        edge=b5.artifact(),
        positive_linkage=cycle_linkage,
        negative_linkage=no_cycle_linkage,
        macro_linkage={"symbols": {}, "call_graph": {"fact": ["fact"]}},
        embedded_linkage={"symbols": {}, "call_graph": {"ADC_Process": ["ADC_Process"]}},
        edge_linkage=empty_linkage,
    )


PHASE64_SUITE_BUILDERS = [
    rule_16_1,
    rule_14_3,
    rule_1_3,
    rule_13_2,
    rule_17_8,
    rule_8_13,
    rule_22_1,
    rule_22_2,
    rule_22_3,
    rule_22_9,
    rule_22_10,
    rule_17_2,
]
