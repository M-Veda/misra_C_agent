"""Phase 6.5 conformance fixtures — five case kinds per alias_analysis ready_now rule."""

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


def _pointer_arith_violation() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "advance"})
    body = b.node("CompoundStmt", parent=fn)
    b.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "buffer"},
        type_information={"is_array": True, "array_size": 8},
    )
    ptr = b.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "ptr"},
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )
    addr = b.node("UnaryOperator", parent=ptr, semantic_properties={"opcode": "&"})
    b.node("DeclRefExpr", parent=addr, semantic_properties={"name": "buffer"})
    arith = b.node(
        "BinaryOperator",
        parent=body,
        semantic_properties={
            "opcode": "+",
            "is_pointer_arithmetic": True,
            "pointer_name": "ptr",
            "offset_exceeds_array_size": True,
        },
    )
    b.node("DeclRefExpr", parent=arith, semantic_properties={"name": "ptr"})
    b.node("IntegerLiteral", parent=arith, semantic_properties={"value": "16"})
    return b.artifact()


def _pointer_arith_compliant() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "index"})
    body = b.node("CompoundStmt", parent=fn)
    b.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "buffer"},
        type_information={"is_array": True, "array_size": 8},
    )
    access = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=access, semantic_properties={"name": "value"})
    idx = b.node("ArraySubscriptExpr", parent=access)
    b.node("DeclRefExpr", parent=idx, semantic_properties={"name": "buffer"})
    b.node("IntegerLiteral", parent=idx, semantic_properties={"value": "3"})
    return b.artifact()


def _memcpy_incompatible() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy"})
    body = b.node("CompoundStmt", parent=fn)
    call = b.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "memcpy", "incompatible_pointer_args": True},
    )
    b.node(
        "DeclRefExpr",
        parent=call,
        semantic_properties={"name": "dest"},
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )
    b.node(
        "DeclRefExpr",
        parent=call,
        semantic_properties={"name": "src"},
        type_information={"is_pointer": True, "pointee_type": "uint16_t"},
    )
    return b.artifact()


def _memcpy_compatible() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy"})
    body = b.node("CompoundStmt", parent=fn)
    call = b.node("CallExpr", parent=body, semantic_properties={"callee": "memcpy"})
    b.node(
        "DeclRefExpr",
        parent=call,
        semantic_properties={"name": "dest"},
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )
    b.node(
        "DeclRefExpr",
        parent=call,
        semantic_properties={"name": "src"},
        type_information={"is_pointer": True, "pointee_type": "uint8_t"},
    )
    return b.artifact()


def _strcpy_overflow() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy_str"})
    body = b.node("CompoundStmt", parent=fn)
    b.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "strcpy", "string_buffer_overflow": True},
    )
    return b.artifact()


def _strcpy_safe() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy_str"})
    body = b.node("CompoundStmt", parent=fn)
    b.node("CallExpr", parent=body, semantic_properties={"callee": "strncpy"})
    return b.artifact()


def _memcpy_oversize() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy_block"})
    body = b.node("CompoundStmt", parent=fn)
    b.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "memcpy", "size_exceeds_destination": True},
    )
    return b.artifact()


def _memcpy_bounded() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy_block"})
    body = b.node("CompoundStmt", parent=fn)
    b.node("CallExpr", parent=body, semantic_properties={"callee": "memcpy"})
    return b.artifact()


def _strtok_use_after() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "parse"})
    body = b.node("CompoundStmt", parent=fn)
    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="}, line=5)
    b.node(
        "DeclRefExpr",
        parent=assign,
        semantic_properties={"name": "token"},
        type_information={"is_pointer": True},
    )
    first = b.node("CallExpr", parent=assign, semantic_properties={"callee": "strtok"}, line=5)
    b.node("DeclRefExpr", parent=first, semantic_properties={"name": "buffer"})
    second = b.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "strtok", "invalidated_pointers": ["token"]},
        line=10,
    )
    b.node("DeclRefExpr", parent=second, semantic_properties={"name": "buffer"})
    use = b.node("DeclRefExpr", parent=body, semantic_properties={"name": "token"}, line=15)
    return b.artifact()


def _strtok_safe() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "parse"})
    body = b.node("CompoundStmt", parent=fn)
    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="}, line=5)
    b.node("DeclRefExpr", parent=assign, semantic_properties={"name": "token"})
    call = b.node("CallExpr", parent=assign, semantic_properties={"callee": "strtok"}, line=5)
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "buffer"})
    use = b.node("DeclRefExpr", parent=body, semantic_properties={"name": "token"}, line=8)
    return b.artifact()


def _fclose_use_after() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "close_and_use"})
    body = b.node("CompoundStmt", parent=fn)
    stream = b.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "stream"},
        type_information={"is_pointer": True, "pointee_type": "FILE"},
        line=3,
    )
    close = b.node("CallExpr", parent=body, semantic_properties={"callee": "fclose"}, line=5)
    b.node("DeclRefExpr", parent=close, semantic_properties={"name": "stream"})
    use = b.node(
        "DeclRefExpr",
        parent=body,
        semantic_properties={"name": "stream"},
        type_information={"is_pointer": True, "pointee_type": "FILE"},
        line=10,
    )
    return b.artifact()


def _fclose_safe() -> dict:
    b = Builder()
    fn = b.node("FunctionDecl", semantic_properties={"name": "close_only"})
    body = b.node("CompoundStmt", parent=fn)
    stream = b.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "stream"},
        type_information={"is_pointer": True, "pointee_type": "FILE"},
    )
    close = b.node("CallExpr", parent=body, semantic_properties={"callee": "fclose"})
    b.node("DeclRefExpr", parent=close, semantic_properties={"name": "stream"})
    return b.artifact()


def rule_18_1() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-18-1",
        _pointer_arith_violation(),
        _pointer_arith_compliant(),
        macro=_pointer_arith_violation(),
        embedded=_pointer_arith_violation(),
        edge=_pointer_arith_compliant(),
    )


def rule_21_15() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-21-15",
        _memcpy_incompatible(),
        _memcpy_compatible(),
    )


def rule_21_17() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-21-17",
        _strcpy_overflow(),
        _strcpy_safe(),
    )


def rule_21_18() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-21-18",
        _memcpy_oversize(),
        _memcpy_bounded(),
    )


def rule_21_20() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-21-20",
        _strtok_use_after(),
        _strtok_safe(),
    )


def rule_22_6() -> RuleConformanceSuite:
    return _five(
        "misra-c2012-rule-22-6",
        _fclose_use_after(),
        _fclose_safe(),
    )


PHASE65_SUITE_BUILDERS = [
    rule_18_1,
    rule_21_15,
    rule_21_17,
    rule_21_18,
    rule_21_20,
    rule_22_6,
]
