"""Phase 6.3 conformance fixtures — five case kinds per type-system ready_now rule."""

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


def rule_10_6() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    assign = non_compliant.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    non_compliant.node("DeclRefExpr", parent=assign, essential_type="unsigned_int")
    non_compliant.node(
        "BinaryOperator",
        parent=assign,
        essential_type="unsigned_long",
        semantic_properties={"opcode": "+", "is_composite_expression": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    assign2 = compliant.node("BinaryOperator", parent=body2, semantic_properties={"opcode": "="})
    compliant.node("DeclRefExpr", parent=assign2, essential_type="unsigned_long")
    compliant.node("DeclRefExpr", parent=assign2, essential_type="unsigned_int")

    return _five(
        "misra-c2012-rule-10-6",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_10_8() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    add = non_compliant.node("BinaryOperator", parent=body, semantic_properties={"opcode": "+"})
    cast = non_compliant.node(
        "CStyleCastExpr",
        parent=add,
        essential_type="float",
        semantic_properties={"is_composite_operand": True},
    )
    non_compliant.node(
        "BinaryOperator",
        parent=cast,
        essential_type="signed_int",
        semantic_properties={"opcode": "+", "is_composite_expression": True},
    )
    non_compliant.node("DeclRefExpr", parent=add, essential_type="signed_int")

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    add2 = compliant.node("BinaryOperator", parent=body2, semantic_properties={"opcode": "+"})
    cast2 = compliant.node("CStyleCastExpr", parent=add2, essential_type="signed_int")
    compliant.node("DeclRefExpr", parent=cast2, essential_type="signed_int")
    compliant.node("DeclRefExpr", parent=add2, essential_type="signed_int")

    return _five(
        "misra-c2012-rule-10-8",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_11_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    cast = non_compliant.node(
        "CStyleCastExpr",
        parent=body,
        type_information={"is_pointer": True, "pointee_type": "uint16_t", "spelling": "uint16_t *"},
    )
    non_compliant.node(
        "DeclRefExpr",
        parent=cast,
        type_information={"is_pointer": True, "pointee_type": "uint8_t", "spelling": "uint8_t *"},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    cast2 = compliant.node(
        "CStyleCastExpr",
        parent=body2,
        type_information={"is_pointer": True, "pointee_type": "void", "spelling": "void *"},
    )
    compliant.node(
        "DeclRefExpr",
        parent=cast2,
        type_information={"is_pointer": True, "pointee_type": "uint8_t", "spelling": "uint8_t *"},
    )

    return _five(
        "misra-c2012-rule-11-3",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_11_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    cast = non_compliant.node(
        "CStyleCastExpr",
        parent=body,
        essential_type="double",
        type_information={"is_pointer": False},
    )
    non_compliant.node(
        "DeclRefExpr",
        parent=cast,
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    cast2 = compliant.node(
        "CStyleCastExpr",
        parent=body2,
        essential_type="unsigned_long",
        type_information={"is_integer": True},
    )
    compliant.node(
        "DeclRefExpr",
        parent=cast2,
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )

    return _five(
        "misra-c2012-rule-11-7",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_12_2() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "BinaryOperator",
        parent=body,
        semantic_properties={"opcode": "<<", "shift_amount": 32, "shift_width": 32},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "BinaryOperator",
        parent=body2,
        semantic_properties={"opcode": "<<", "shift_amount": 3, "shift_width": 32},
    )

    return _five(
        "misra-c2012-rule-12-2",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_12_4() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "BinaryOperator",
        parent=body,
        essential_type="unsigned_short",
        semantic_properties={"opcode": "+", "wraps_on_evaluation": True, "is_constant_unsigned": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "BinaryOperator",
        parent=body2,
        essential_type="unsigned_int",
        semantic_properties={"opcode": "+"},
    )

    return _five(
        "misra-c2012-rule-12-4",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_14_1() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "ForStmt",
        parent=body,
        semantic_properties={"loop_counter_essential_type": "float"},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    for_stmt = compliant.node("ForStmt", parent=body2)
    compliant.node("VarDecl", parent=for_stmt, essential_type="unsigned_int", semantic_properties={"name": "i"})

    return _five(
        "misra-c2012-rule-14-1",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_16_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    switch = non_compliant.node("SwitchStmt", parent=body)
    non_compliant.node("DeclRefExpr", parent=switch, essential_type="boolean", semantic_properties={"name": "flag"})
    non_compliant.node("CompoundStmt", parent=switch)

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    switch2 = compliant.node("SwitchStmt", parent=body2)
    compliant.node("DeclRefExpr", parent=switch2, essential_type="signed_int", semantic_properties={"name": "mode"})
    compliant.node("CompoundStmt", parent=switch2)

    return _five(
        "misra-c2012-rule-16-7",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_21_14() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "memcmp", "compares_null_terminated_strings": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "CallExpr",
        parent=body2,
        semantic_properties={"callee": "memcmp"},
    )

    return _five(
        "misra-c2012-rule-21-14",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_21_16() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    call = non_compliant.node("CallExpr", parent=body, semantic_properties={"callee": "memcmp"})
    non_compliant.node(
        "DeclRefExpr",
        parent=call,
        semantic_properties={"name": "struct_a", "invalid_pointer_argument": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    call2 = compliant.node("CallExpr", parent=body2, semantic_properties={"callee": "memcmp"})
    compliant.node(
        "DeclRefExpr",
        parent=call2,
        semantic_properties={"name": "buffer"},
        essential_type="unsigned_char",
    )

    return _five(
        "misra-c2012-rule-21-16",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_21_19() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "DeclRefExpr",
        parent=body,
        semantic_properties={"name": "locale_text", "returned_pointer_missing_const": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "DeclRefExpr",
        parent=body2,
        semantic_properties={"name": "locale_text"},
        qualifiers=["const"],
    )

    return _five(
        "misra-c2012-rule-21-19",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_5() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    deref = non_compliant.node("UnaryOperator", parent=body, semantic_properties={"opcode": "*"})
    non_compliant.node(
        "DeclRefExpr",
        parent=deref,
        type_information={"is_pointer": True, "pointee_type": "FILE", "spelling": "FILE *"},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    compliant.node(
        "CallExpr",
        parent=body2,
        semantic_properties={"callee": "fgetc"},
    )

    return _five(
        "misra-c2012-rule-22-5",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_22_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    non_compliant.node(
        "BinaryOperator",
        parent=body,
        semantic_properties={"opcode": "==", "eof_operand_modified": True},
    )

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    assign = compliant.node("BinaryOperator", parent=body2, semantic_properties={"opcode": "="})
    compliant.node(
        "CallExpr",
        parent=assign,
        semantic_properties={"callee": "fgetc"},
    )
    compliant.node("DeclRefExpr", parent=assign, semantic_properties={"name": "ch"})

    return _five(
        "misra-c2012-rule-22-7",
        non_compliant.artifact(),
        compliant.artifact(),
    )


def rule_8_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node(
        "VarDecl",
        semantic_properties={"name": "sensor_count", "declaration_incompatible": True},
        essential_type="signed_int",
    )
    non_compliant.node(
        "VarDecl",
        semantic_properties={"name": "sensor_count"},
        essential_type="signed_int",
        qualifiers=["const"],
    )

    compliant = Builder()
    compliant.node(
        "VarDecl",
        semantic_properties={"name": "sensor_count"},
        essential_type="signed_int",
    )
    compliant.node(
        "VarDecl",
        semantic_properties={"name": "sensor_count"},
        essential_type="signed_int",
    )

    return _five(
        "misra-c2012-rule-8-3",
        non_compliant.artifact(),
        compliant.artifact(),
    )


PHASE63_SUITE_BUILDERS = [
    rule_8_3,
    rule_10_6,
    rule_10_8,
    rule_11_3,
    rule_11_7,
    rule_12_2,
    rule_12_4,
    rule_14_1,
    rule_16_7,
    rule_21_14,
    rule_21_16,
    rule_21_19,
    rule_22_5,
    rule_22_7,
]
