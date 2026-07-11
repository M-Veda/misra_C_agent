"""Phase 7.1 conformance fixtures — five case kinds per AST schema v3 metadata rule."""

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


def _preprocessor_artifact(**fields: object) -> dict:
    return {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": dict(fields),
    }


def rule_4_1() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("StringLiteral", semantic_properties={"escape_sequence_terminated": False})
    good = Builder()
    good.node("StringLiteral", semantic_properties={"escape_sequence_terminated": True})
    macro = Builder()
    macro.node(
        "CharacterLiteral",
        semantic_properties={"unterminated_escape": True},
        macro_origin={"macro_name": "CHAR_LIT"},
    )
    embedded = Builder()
    embedded.node("StringLiteral", semantic_properties={"escape_sequence_terminated": False})
    return _five("misra-c2012-rule-4-1", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_7_1() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("IntegerLiteral", semantic_properties={"literal_base": "octal", "value": "010"})
    good = Builder()
    good.node("IntegerLiteral", semantic_properties={"literal_base": "decimal", "value": "10"})
    macro = Builder()
    macro.node(
        "IntegerLiteral",
        semantic_properties={"octal_nonzero_constant": True},
        macro_origin={"macro_name": "OCT"},
    )
    embedded = Builder()
    embedded.node("IntegerLiteral", semantic_properties={"literal_base": "octal"})
    return _five("misra-c2012-rule-7-1", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_7_2() -> RuleConformanceSuite:
    bad = Builder()
    bad.node(
        "IntegerLiteral",
        essential_type="unsigned_int",
        semantic_properties={"missing_u_suffix": True, "value": "0xFFFF"},
    )
    good = Builder()
    good.node(
        "IntegerLiteral",
        essential_type="unsigned_int",
        semantic_properties={"missing_u_suffix": False, "has_u_suffix": True},
    )
    macro = Builder()
    macro.node(
        "IntegerLiteral",
        essential_type="unsigned_long",
        semantic_properties={"missing_u_suffix": True},
        macro_origin={"macro_name": "MASK"},
    )
    embedded = Builder()
    embedded.node("IntegerLiteral", essential_type="unsigned_int", semantic_properties={"missing_u_suffix": True})
    return _five("misra-c2012-rule-7-2", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_7_3() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("IntegerLiteral", semantic_properties={"uses_lowercase_l_suffix": True})
    good = Builder()
    good.node("IntegerLiteral", semantic_properties={"uses_lowercase_l_suffix": False, "has_l_suffix": True})
    macro = Builder()
    macro.node(
        "IntegerLiteral",
        semantic_properties={"uses_lowercase_l_suffix": True},
        macro_origin={"macro_name": "LONG_VAL"},
    )
    embedded = Builder()
    embedded.node("IntegerLiteral", semantic_properties={"uses_lowercase_l_suffix": True})
    return _five("misra-c2012-rule-7-3", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_12_1() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("BinaryOperator", semantic_properties={"opcode": "+", "needs_explicit_parentheses": True})
    good = Builder()
    good.node("BinaryOperator", semantic_properties={"opcode": "+", "needs_explicit_parentheses": False})
    macro = Builder()
    macro.node(
        "BinaryOperator",
        semantic_properties={"opcode": "*", "needs_explicit_parentheses": True},
        macro_origin={"macro_name": "EXPR"},
    )
    embedded = Builder()
    embedded.node("BinaryOperator", semantic_properties={"needs_explicit_parentheses": True})
    return _five("misra-c2012-rule-12-1", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_12_5() -> RuleConformanceSuite:
    bad = Builder()
    fn = bad.node("FunctionDecl", semantic_properties={"name": "f"})
    body = bad.node("CompoundStmt", parent=fn)
    bad.node(
        "UnaryOperator",
        parent=body,
        semantic_properties={"opcode": "sizeof", "sizeof_operand_is_decayed_array": True},
    )
    good = Builder()
    fn2 = good.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = good.node("CompoundStmt", parent=fn2)
    good.node("UnaryOperator", parent=body2, semantic_properties={"opcode": "sizeof"})
    macro = Builder()
    fn3 = macro.node("FunctionDecl", semantic_properties={"name": "f"})
    body3 = macro.node("CompoundStmt", parent=fn3)
    macro.node(
        "UnaryOperator",
        parent=body3,
        semantic_properties={"opcode": "sizeof", "sizeof_operand_is_decayed_array": True},
        macro_origin={"macro_name": "SZ"},
    )
    embedded = bad.artifact()
    return _five("misra-c2012-rule-12-5", bad.artifact(), good.artifact(), macro.artifact(), embedded)


def rule_6_1() -> RuleConformanceSuite:
    bad = Builder()
    bad.node(
        "FieldDecl",
        semantic_properties={"name": "flags", "is_bit_field": True, "invalid_bit_field_type": True},
    )
    good = Builder()
    good.node(
        "FieldDecl",
        semantic_properties={
            "name": "ready",
            "is_bit_field": True,
            "bit_field_type_category": "unsigned_int",
        },
    )
    macro = Builder()
    macro.node(
        "FieldDecl",
        semantic_properties={"is_bit_field": True, "bit_field_type_category": "uint8_t"},
        macro_origin={"macro_name": "BF"},
    )
    embedded = Builder()
    embedded.node("FieldDecl", semantic_properties={"invalid_bit_field_type": True})
    return _five("misra-c2012-rule-6-1", bad.artifact(), good.artifact(), macro.artifact(), embedded.artifact())


def rule_6_2() -> RuleConformanceSuite:
    bad = Builder()
    bad.node(
        "FieldDecl",
        semantic_properties={"name": "flag", "bit_field_width": 1, "bit_field_is_signed": True},
    )
    good = Builder()
    good.node(
        "FieldDecl",
        semantic_properties={"name": "flag", "bit_field_width": 1, "bit_field_is_signed": False},
    )
    macro = Builder()
    macro.node(
        "FieldDecl",
        semantic_properties={"bit_field_width": 1, "bit_field_is_signed": True},
        macro_origin={"macro_name": "BIT"},
    )
    embedded = bad.artifact()
    edge = Builder()
    edge.node("FieldDecl", semantic_properties={"bit_field_width": 2, "bit_field_is_signed": True})
    return _five("misra-c2012-rule-6-2", bad.artifact(), good.artifact(), macro.artifact(), embedded, edge.artifact())


def rule_8_11() -> RuleConformanceSuite:
    bad = Builder()
    bad.node(
        "VarDecl",
        semantic_properties={"name": "buffer", "linkage": "external", "missing_array_size": True},
        type_information={"is_array": True},
    )
    good = Builder()
    good.node(
        "VarDecl",
        semantic_properties={"name": "buffer", "linkage": "external"},
        type_information={"is_array": True, "array_size": 64},
    )
    macro = Builder()
    macro.node(
        "VarDecl",
        semantic_properties={"linkage": "external", "missing_array_size": True},
        type_information={"is_array": True},
        macro_origin={"macro_name": "BUF"},
    )
    embedded = bad.artifact()
    return _five("misra-c2012-rule-8-11", bad.artifact(), good.artifact(), macro.artifact(), embedded)


def rule_8_12() -> RuleConformanceSuite:
    bad = Builder()
    enum_id = bad.node("EnumDecl", semantic_properties={"name": "mode_tag"})
    bad.node(
        "EnumConstantDecl",
        parent=enum_id,
        semantic_properties={"name": "MODE_A", "duplicate_implicit_enumerator": True},
    )
    good = Builder()
    enum2 = good.node("EnumDecl", semantic_properties={"name": "mode_tag"})
    good.node("EnumConstantDecl", parent=enum2, semantic_properties={"name": "MODE_A", "enumerator_value": 0})
    good.node("EnumConstantDecl", parent=enum2, semantic_properties={"name": "MODE_B", "enumerator_value": 1})
    macro = bad.artifact()
    embedded = bad.artifact()
    edge = Builder()
    enum3 = edge.node("EnumDecl")
    edge.node(
        "EnumConstantDecl",
        parent=enum3,
        semantic_properties={"is_implicit_enumerator": True, "enumerator_value": 0},
    )
    edge.node(
        "EnumConstantDecl",
        parent=enum3,
        semantic_properties={"is_implicit_enumerator": True, "enumerator_value": 0},
    )
    return _suite(
        "misra-c2012-rule-8-12",
        [
            ConformanceCase("pos-1", "positive", bad.artifact(), True),
            ConformanceCase("neg-1", "negative", good.artifact(), False),
            ConformanceCase("macro-1", "macro", macro, True),
            ConformanceCase("embedded-1", "embedded", embedded, True),
            ConformanceCase("edge-1", "edge", edge.artifact(), True),
        ],
    )


def rule_17_5() -> RuleConformanceSuite:
    bad = Builder()
    fn = bad.node("FunctionDecl", semantic_properties={"name": "copy"})
    body = bad.node("CompoundStmt", parent=fn)
    bad.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "copy", "call_argument_shape_mismatch": True},
    )
    good = Builder()
    fn2 = good.node("FunctionDecl", semantic_properties={"name": "copy"})
    body2 = good.node("CompoundStmt", parent=fn2)
    good.node("CallExpr", parent=body2, semantic_properties={"callee": "copy"})
    macro = bad.artifact()
    embedded = bad.artifact()
    return _five("misra-c2012-rule-17-5", bad.artifact(), good.artifact(), macro, embedded)


def rule_18_8() -> RuleConformanceSuite:
    bad = Builder()
    fn = bad.node("FunctionDecl", semantic_properties={"name": "f"})
    body = bad.node("CompoundStmt", parent=fn)
    bad.node(
        "VarDecl",
        parent=body,
        semantic_properties={"name": "buffer"},
        type_information={"is_variable_length_array": True},
    )
    good = Builder()
    good.node("VarDecl", semantic_properties={"name": "buffer"}, type_information={"is_array": True, "array_size": 8})
    macro = bad.artifact()
    embedded = bad.artifact()
    return _five("misra-c2012-rule-18-8", bad.artifact(), good.artifact(), macro, embedded)


def rule_9_2() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("InitListExpr", semantic_properties={"is_fully_bracketed": False})
    good = Builder()
    good.node("InitListExpr", semantic_properties={"is_fully_bracketed": True})
    macro = Builder()
    macro.node(
        "InitListExpr",
        semantic_properties={"is_fully_bracketed": False},
        macro_origin={"macro_name": "INIT"},
    )
    embedded = bad.artifact()
    return _five("misra-c2012-rule-9-2", bad.artifact(), good.artifact(), macro.artifact(), embedded)


def rule_9_4() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("InitListExpr", semantic_properties={"duplicate_designator": True})
    good = Builder()
    good.node("InitListExpr", semantic_properties={"duplicate_designator": False})
    macro = bad.artifact()
    embedded = bad.artifact()
    return _five("misra-c2012-rule-9-4", bad.artifact(), good.artifact(), macro, embedded)


def rule_11_2() -> RuleConformanceSuite:
    bad = Builder()
    bad.node("CStyleCastExpr", semantic_properties={"converts_to_incomplete": True})
    good = Builder()
    good.node("CStyleCastExpr", semantic_properties={"converts_to_incomplete": False})
    macro = Builder()
    macro.node(
        "CStyleCastExpr",
        semantic_properties={"converts_from_incomplete": True},
        macro_origin={"macro_name": "CAST"},
    )
    embedded = bad.artifact()
    return _five("misra-c2012-rule-11-2", bad.artifact(), good.artifact(), macro.artifact(), embedded)


def rule_18_5() -> RuleConformanceSuite:
    bad = Builder()
    bad.node(
        "VarDecl",
        semantic_properties={"name": "deep"},
        type_information={"pointer_nesting_depth": 3, "is_pointer": True},
    )
    good = Builder()
    good.node(
        "VarDecl",
        semantic_properties={"name": "ptr"},
        type_information={"pointer_nesting_depth": 2, "is_pointer": True},
    )
    macro = Builder()
    macro.node(
        "ParmVarDecl",
        semantic_properties={"name": "arg"},
        type_information={"pointer_nesting_depth": 4},
        macro_origin={"macro_name": "DEEP"},
    )
    embedded = bad.artifact()
    edge = Builder()
    edge.node("VarDecl", type_information={"pointer_nesting_depth": 2})
    return _five("misra-c2012-rule-18-5", bad.artifact(), good.artifact(), macro.artifact(), embedded, edge.artifact())


def rule_20_5() -> RuleConformanceSuite:
    bad = _preprocessor_artifact(undef_directives=[{"name": "FEATURE", "range": {"line_start": 2}}])
    good = _preprocessor_artifact(macro_definitions=[{"name": "FEATURE", "value": "1"}])
    macro = _preprocessor_artifact(
        undef_directives=[{"name": "TEMP", "range": {"line_start": 5}}],
        macro_definitions=[{"name": "TEMP", "value": "0"}],
    )
    embedded = bad
    edge = _preprocessor_artifact()
    return _five("misra-c2012-rule-20-5", bad, good, macro, embedded, edge)


def rule_20_10() -> RuleConformanceSuite:
    bad = _preprocessor_artifact(
        macro_definitions=[{"name": "STR", "uses_stringify": True, "range": {"line_start": 1}}]
    )
    good = _preprocessor_artifact(macro_definitions=[{"name": "MAX", "value": "10"}])
    macro = _preprocessor_artifact(
        macro_definitions=[{"name": "JOIN", "uses_token_paste": True, "range": {"line_start": 3}}]
    )
    embedded = _preprocessor_artifact(
        macro_definitions=[
            {"name": "BOTH", "uses_stringify": True, "uses_token_paste": True, "range": {"line_start": 4}}
        ]
    )
    edge = _preprocessor_artifact()
    return _five("misra-c2012-rule-20-10", bad, good, macro, embedded, edge)


def rule_21_13() -> RuleConformanceSuite:
    bad = Builder()
    fn = bad.node("FunctionDecl", semantic_properties={"name": "check"})
    body = bad.node("CompoundStmt", parent=fn)
    bad.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "isalpha", "argument_may_be_negative_char": True},
    )
    good = Builder()
    fn2 = good.node("FunctionDecl", semantic_properties={"name": "check"})
    body2 = good.node("CompoundStmt", parent=fn2)
    good.node("CallExpr", parent=body2, semantic_properties={"callee": "isalpha"})
    macro = bad.artifact()
    embedded = bad.artifact()
    return _five("misra-c2012-rule-21-13", bad.artifact(), good.artifact(), macro, embedded)


def rule_22_4() -> RuleConformanceSuite:
    bad = Builder()
    fn = bad.node("FunctionDecl", semantic_properties={"name": "log_read"})
    body = bad.node("CompoundStmt", parent=fn)
    bad.node(
        "CallExpr",
        parent=body,
        semantic_properties={"callee": "fprintf", "writes_to_readonly_stream": True},
    )
    good = Builder()
    fn2 = good.node("FunctionDecl", semantic_properties={"name": "log_write"})
    body2 = good.node("CompoundStmt", parent=fn2)
    good.node("CallExpr", parent=body2, semantic_properties={"callee": "fprintf"})
    macro = bad.artifact()
    embedded = bad.artifact()
    return _five("misra-c2012-rule-22-4", bad.artifact(), good.artifact(), macro, embedded)


PHASE71_SUITE_BUILDERS = [
    rule_4_1,
    rule_6_1,
    rule_6_2,
    rule_7_1,
    rule_7_2,
    rule_7_3,
    rule_8_11,
    rule_8_12,
    rule_9_2,
    rule_9_4,
    rule_11_2,
    rule_12_1,
    rule_12_5,
    rule_17_5,
    rule_18_5,
    rule_18_8,
    rule_20_5,
    rule_20_10,
    rule_21_13,
    rule_22_4,
]
