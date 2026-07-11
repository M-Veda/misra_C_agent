"""Conformance fixtures for every rule implemented in Phase 3 (plus the
Phase 1.2/1.3 pilot rules). Each function builds a small `RuleConformanceSuite`
with at least a positive and a negative case; several add edge/macro/embedded
cases too. These fixtures double as functional tests of `detect()` logic and
as the input to the precision/recall/false-positive-rate report."""

from conformance.ast_builders import Builder
from conformance.fixtures_phase6 import PHASE6_SUITE_BUILDERS
from conformance.fixtures_phase62 import PHASE62_SUITE_BUILDERS
from conformance.fixtures_phase63 import PHASE63_SUITE_BUILDERS
from conformance.fixtures_phase64 import PHASE64_SUITE_BUILDERS
from conformance.fixtures_phase65 import PHASE65_SUITE_BUILDERS
from conformance.fixtures_phase71 import PHASE71_SUITE_BUILDERS
from misra_platform_rules.conformance import ConformanceCase, RuleConformanceSuite


def _suite(rule_id: str, cases: list[ConformanceCase]) -> RuleConformanceSuite:
    return RuleConformanceSuite(rule_id=rule_id, cases=cases)


def rule_10_1() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b1.node("DeclRefExpr", parent=op, essential_type="boolean")
    b1.node("DeclRefExpr", parent=op, essential_type="signed_int")

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_int")
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_int")

    return _suite(
        "misra-c2012-rule-10-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_10_2() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b1.node("DeclRefExpr", parent=op, essential_type="char")
    b1.node("DeclRefExpr", parent=op, essential_type="unsigned_int")

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_int")
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_int")

    return _suite(
        "misra-c2012-rule-10-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_10_3() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "="})
    b1.node("DeclRefExpr", parent=op, essential_type="unsigned_char")
    b1.node("DeclRefExpr", parent=op, essential_type="unsigned_int")

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "="})
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_int")
    b2.node("DeclRefExpr", parent=op2, essential_type="unsigned_char")

    return _suite(
        "misra-c2012-rule-10-3",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_10_4() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b1.node("DeclRefExpr", parent=op, essential_type="signed_int")
    b1.node("DeclRefExpr", parent=op, essential_type="float")

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b2.node("DeclRefExpr", parent=op2, essential_type="signed_int")
    b2.node("DeclRefExpr", parent=op2, essential_type="signed_long")

    return _suite(
        "misra-c2012-rule-10-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_10_5() -> RuleConformanceSuite:
    b1 = Builder()
    cast = b1.node("CStyleCastExpr", essential_type="float")
    b1.node("DeclRefExpr", parent=cast, essential_type="signed_int")

    b2 = Builder()
    cast2 = b2.node("CStyleCastExpr", essential_type="signed_long")
    b2.node("DeclRefExpr", parent=cast2, essential_type="signed_int")

    return _suite(
        "misra-c2012-rule-10-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_10_7() -> RuleConformanceSuite:
    b1 = Builder()
    outer = b1.node("BinaryOperator", semantic_properties={"opcode": "+"})
    cast = b1.node("CStyleCastExpr", parent=outer, essential_type="float")
    b1.node("BinaryOperator", parent=cast, semantic_properties={"opcode": "*"}, essential_type="signed_int")
    b1.node("DeclRefExpr", parent=outer, essential_type="boolean")

    b2 = Builder()
    outer2 = b2.node("BinaryOperator", semantic_properties={"opcode": "+"})
    cast2 = b2.node("CStyleCastExpr", parent=outer2, essential_type="signed_int")
    b2.node("BinaryOperator", parent=cast2, semantic_properties={"opcode": "*"}, essential_type="signed_int")
    b2.node("DeclRefExpr", parent=outer2, essential_type="signed_long")

    return _suite(
        "misra-c2012-rule-10-7",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_8_2() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl", semantic_properties={"name": "set_speed"})
    b1.node("ParmVarDecl", parent=fn, semantic_properties={})

    b2 = Builder()
    fn2 = b2.node("FunctionDecl", semantic_properties={"name": "set_speed"})
    b2.node("ParmVarDecl", parent=fn2, semantic_properties={"name": "speed_kph"})

    return _suite(
        "misra-c2012-rule-8-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_8_4() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl", semantic_properties={"name": "foo", "storage_class": "external"})
    b1.node("CompoundStmt", parent=fn)

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "foo", "storage_class": "external"})
    fn_def = b2.node("FunctionDecl", semantic_properties={"name": "foo", "storage_class": "external"})
    b2.node("CompoundStmt", parent=fn_def)

    return _suite(
        "misra-c2012-rule-8-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_8_6() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "shared_fn", "storage_class": "external"})
    linkage_multi = {
        "symbols": {
            "shared_fn": [
                {"translation_unit_id": "tu1", "file_path": "a.c", "storage_class": "external", "has_body": True, "type_spelling": "", "node_kind": "FunctionDecl"},
                {"translation_unit_id": "tu2", "file_path": "b.c", "storage_class": "external", "has_body": True, "type_spelling": "", "node_kind": "FunctionDecl"},
            ]
        }
    }

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "shared_fn", "storage_class": "external"})

    return _suite(
        "misra-c2012-rule-8-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage_multi),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=None),
        ],
    )


def rule_8_14() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("ParmVarDecl", qualifiers=["restrict"], semantic_properties={"name": "dest"})

    b2 = Builder()
    b2.node("ParmVarDecl", qualifiers=[], semantic_properties={"name": "dest"})

    return _suite(
        "misra-c2012-rule-8-14",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_11_4() -> RuleConformanceSuite:
    b1 = Builder()
    cast = b1.node("CStyleCastExpr", type_information={"is_pointer": True})
    b1.node("DeclRefExpr", parent=cast, type_information={"is_integer": True})

    b2 = Builder()
    cast2 = b2.node("CStyleCastExpr", type_information={"is_pointer": True})
    b2.node("DeclRefExpr", parent=cast2, type_information={})

    return _suite(
        "misra-c2012-rule-11-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_11_5() -> RuleConformanceSuite:
    b1 = Builder()
    cast = b1.node("CStyleCastExpr", type_information={"is_pointer": True, "pointee_type": "sensor_t"})
    b1.node("DeclRefExpr", parent=cast, type_information={"is_pointer": True, "pointee_type": "void"})

    b2 = Builder()
    cast2 = b2.node("CStyleCastExpr", type_information={"is_pointer": True, "pointee_type": "sensor_t"})
    b2.node("DeclRefExpr", parent=cast2, type_information={"is_pointer": True, "pointee_type": "int"})

    return _suite(
        "misra-c2012-rule-11-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_11_8() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node(
        "CStyleCastExpr",
        semantic_properties={"removes_qualifier": True, "removed_qualifiers": ["const"]},
    )

    b2 = Builder()
    b2.node("CStyleCastExpr", semantic_properties={"removes_qualifier": False})

    return _suite(
        "misra-c2012-rule-11-8",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_11_9() -> RuleConformanceSuite:
    b1 = Builder()
    cast = b1.node("CStyleCastExpr", type_information={"is_pointer": True})
    b1.node("IntegerLiteral", parent=cast, semantic_properties={}, macro_origin={})

    b2 = Builder()
    cast2 = b2.node("CStyleCastExpr", type_information={"is_pointer": True})
    b2.node("IntegerLiteral", parent=cast2, semantic_properties={}, macro_origin={"macro_name": "NULL"})

    return _suite(
        "misra-c2012-rule-11-9",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_18_2() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "-"})
    b1.node("DeclRefExpr", parent=op, type_information={"is_pointer": True, "pointee_type": "int"})
    b1.node("DeclRefExpr", parent=op, type_information={"is_pointer": True, "pointee_type": "float"})

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "-"})
    b2.node("DeclRefExpr", parent=op2, type_information={"is_pointer": True, "pointee_type": "int"})
    b2.node("DeclRefExpr", parent=op2, type_information={"is_pointer": True, "pointee_type": "int"})

    return _suite(
        "misra-c2012-rule-18-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_15_1() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("GotoStmt")

    b2 = Builder()
    b2.node("ReturnStmt")

    return _suite(
        "misra-c2012-rule-15-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_15_5() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl")
    body = b1.node("CompoundStmt", parent=fn)
    b1.node("ReturnStmt", parent=body)
    b1.node("ReturnStmt", parent=body)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl")
    body2 = b2.node("CompoundStmt", parent=fn2)
    b2.node("ReturnStmt", parent=body2)

    return _suite(
        "misra-c2012-rule-15-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_15_6() -> RuleConformanceSuite:
    b1 = Builder()
    ifstmt = b1.node("IfStmt")
    b1.node("DeclRefExpr", parent=ifstmt)
    b1.node("ReturnStmt", parent=ifstmt)

    b2 = Builder()
    ifstmt2 = b2.node("IfStmt")
    b2.node("DeclRefExpr", parent=ifstmt2)
    b2.node("CompoundStmt", parent=ifstmt2)

    return _suite(
        "misra-c2012-rule-15-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_16_3() -> RuleConformanceSuite:
    b1 = Builder()
    sw = b1.node("SwitchStmt")
    body = b1.node("CompoundStmt", parent=sw)
    b1.node("CaseStmt", parent=body)
    b1.node("CallExpr", parent=body)
    b1.node("CaseStmt", parent=body)
    b1.node("BreakStmt", parent=body)

    b2 = Builder()
    sw2 = b2.node("SwitchStmt")
    body2 = b2.node("CompoundStmt", parent=sw2)
    b2.node("CaseStmt", parent=body2)
    b2.node("BreakStmt", parent=body2)
    b2.node("CaseStmt", parent=body2)
    b2.node("BreakStmt", parent=body2)

    return _suite(
        "misra-c2012-rule-16-3",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_16_4() -> RuleConformanceSuite:
    b1 = Builder()
    sw = b1.node("SwitchStmt")
    b1.node("CaseStmt", parent=sw)

    b2 = Builder()
    sw2 = b2.node("SwitchStmt")
    b2.node("CaseStmt", parent=sw2)
    b2.node("DefaultStmt", parent=sw2)

    return _suite(
        "misra-c2012-rule-16-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_16_6() -> RuleConformanceSuite:
    b1 = Builder()
    sw = b1.node("SwitchStmt")
    b1.node("CaseStmt", parent=sw)

    b2 = Builder()
    sw2 = b2.node("SwitchStmt")
    b2.node("CaseStmt", parent=sw2)
    b2.node("CaseStmt", parent=sw2)
    b2.node("DefaultStmt", parent=sw2)

    return _suite(
        "misra-c2012-rule-16-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_20_4() -> RuleConformanceSuite:
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "for", "value": "while", "is_function_like": False, "range": {}}]
        },
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "MAX_RETRIES", "value": "3", "is_function_like": False, "range": {}}]
        },
    }
    return _suite(
        "misra-c2012-rule-20-4",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
        ],
    )


def rule_20_7() -> RuleConformanceSuite:
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "SQUARE", "value": "x * x", "is_function_like": True, "range": {}}]
        },
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [
                {"name": "SQUARE", "value": "((x) * (x))", "is_function_like": True, "range": {}}
            ]
        },
    }
    return _suite(
        "misra-c2012-rule-20-7",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
        ],
    )


def rule_20_14() -> RuleConformanceSuite:
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {"conditional_branches": [{"directive": "if", "taken": True, "range": {}}]},
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "conditional_branches": [
                {"directive": "if", "taken": True, "range": {}},
                {"directive": "endif", "taken": True, "range": {}},
            ]
        },
    }
    return _suite(
        "misra-c2012-rule-20-14",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
        ],
    )


def rule_21_1() -> RuleConformanceSuite:
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "_RESERVED", "value": "1", "is_function_like": False, "range": {}}]
        },
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "APP_MAX", "value": "1", "is_function_like": False, "range": {}}]
        },
    }
    return _suite(
        "misra-c2012-rule-21-1",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
        ],
    )


def rule_12_3() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("BinaryOperator", semantic_properties={"opcode": ","})

    b2 = Builder()
    b2.node("BinaryOperator", semantic_properties={"opcode": "+"})

    return _suite(
        "misra-c2012-rule-12-3",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_13_4() -> RuleConformanceSuite:
    b1 = Builder()
    ifstmt = b1.node("IfStmt")
    b1.node("BinaryOperator", parent=ifstmt, semantic_properties={"opcode": "="})

    b2 = Builder()
    body = b2.node("CompoundStmt")
    b2.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})

    return _suite(
        "misra-c2012-rule-13-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_13_5() -> RuleConformanceSuite:
    b1 = Builder()
    op = b1.node("BinaryOperator", semantic_properties={"opcode": "&&"})
    b1.node("DeclRefExpr", parent=op)
    b1.node("CallExpr", parent=op)

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "&&"})
    b2.node("DeclRefExpr", parent=op2)
    b2.node("DeclRefExpr", parent=op2)

    return _suite(
        "misra-c2012-rule-13-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_14_4() -> RuleConformanceSuite:
    b1 = Builder()
    ifstmt = b1.node("IfStmt")
    b1.node("DeclRefExpr", parent=ifstmt, essential_type="unsigned_int")
    b1.node("CompoundStmt", parent=ifstmt)

    b2 = Builder()
    ifstmt2 = b2.node("IfStmt")
    b2.node("DeclRefExpr", parent=ifstmt2, essential_type="boolean")
    b2.node("CompoundStmt", parent=ifstmt2)

    return _suite(
        "misra-c2012-rule-14-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_9_1() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl")
    b1.node("VarDecl", parent=fn, semantic_properties={"name": "total"}, line=1)
    b1.node("DeclRefExpr", parent=fn, semantic_properties={"name": "total"}, line=2)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl")
    decl2 = b2.node("VarDecl", parent=fn2, semantic_properties={"name": "total"}, line=1)
    b2.node("IntegerLiteral", parent=decl2, line=1)  # initializer present
    b2.node("DeclRefExpr", parent=fn2, semantic_properties={"name": "total"}, line=2)

    return _suite(
        "misra-c2012-rule-9-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_2_2() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl")
    b1.node("VarDecl", parent=fn, semantic_properties={"name": "result"}, line=1)
    b1.node("DeclRefExpr", parent=fn, semantic_properties={"name": "result"}, line=2)
    assign = b1.node("BinaryOperator", parent=fn, semantic_properties={"opcode": "="}, line=3)
    b1.node("DeclRefExpr", parent=assign, semantic_properties={"name": "result"}, line=3)
    b1.node("IntegerLiteral", parent=assign, line=3)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl")
    b2.node("VarDecl", parent=fn2, semantic_properties={"name": "result"}, line=1)
    assign2 = b2.node("BinaryOperator", parent=fn2, semantic_properties={"opcode": "="}, line=2)
    b2.node("DeclRefExpr", parent=assign2, semantic_properties={"name": "result"}, line=2)
    b2.node("IntegerLiteral", parent=assign2, line=2)
    b2.node("DeclRefExpr", parent=fn2, semantic_properties={"name": "result"}, line=3)

    return _suite(
        "misra-c2012-rule-2-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_8_9() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("VarDecl", semantic_properties={"name": "cache"})
    fn = b1.node("FunctionDecl")
    b1.node("DeclRefExpr", parent=fn, semantic_properties={"name": "cache"})

    b2 = Builder()
    b2.node("VarDecl", semantic_properties={"name": "cache"})
    fn_a = b2.node("FunctionDecl")
    fn_b = b2.node("FunctionDecl")
    b2.node("DeclRefExpr", parent=fn_a, semantic_properties={"name": "cache"})
    b2.node("DeclRefExpr", parent=fn_b, semantic_properties={"name": "cache"})

    return _suite(
        "misra-c2012-rule-8-9",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_18_6() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl")
    b1.node("VarDecl", parent=fn, semantic_properties={"name": "local", "storage_class": "automatic"})
    ret = b1.node("ReturnStmt", parent=fn)
    addr = b1.node("UnaryOperator", parent=ret, semantic_properties={"opcode": "&"})
    b1.node("DeclRefExpr", parent=addr, semantic_properties={"name": "local"})

    b2 = Builder()
    fn2 = b2.node("FunctionDecl")
    b2.node("ParmVarDecl", parent=fn2, semantic_properties={"name": "out"})
    ret2 = b2.node("ReturnStmt", parent=fn2)
    b2.node("DeclRefExpr", parent=ret2, semantic_properties={"name": "out"})

    return _suite(
        "misra-c2012-rule-18-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


def rule_5_1() -> RuleConformanceSuite:
    prefix = "x" * 31
    name1 = prefix + "a"
    name2 = prefix + "b"
    linkage_data = {
        "symbols": {
            name1: [{"translation_unit_id": "tu1", "file_path": "a.c", "storage_class": "external", "has_body": True, "type_spelling": "", "node_kind": "FunctionDecl"}],
            name2: [{"translation_unit_id": "tu2", "file_path": "b.c", "storage_class": "external", "has_body": True, "type_spelling": "", "node_kind": "FunctionDecl"}],
        }
    }
    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": name1})

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "short_name"})

    return _suite(
        "misra-c2012-rule-5-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage_data),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=None),
        ],
    )


def rule_8_7() -> RuleConformanceSuite:
    linkage_single = {
        "symbols": {
            "helper": [
                {"translation_unit_id": "pos-1", "file_path": "a.c", "storage_class": "external", "has_body": True, "type_spelling": "", "node_kind": "FunctionDecl"}
            ]
        }
    }
    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "external"})

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})

    return _suite(
        "misra-c2012-rule-8-7",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage_single),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=linkage_single),
        ],
    )


def rule_8_10() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "clamp", "is_inline": True, "storage_class": "external"})

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "clamp", "is_inline": True, "storage_class": "static"})

    return _suite(
        "misra-c2012-rule-8-10",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
        ],
    )


# ---------------------------------------------------------------------------
# Phase 5: every new rule below carries the full five-kind conformance bar
# (positive/negative/macro/embedded/edge), per the Phase 5 testing mandate.
# ---------------------------------------------------------------------------


def rule_5_2() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("RecordDecl", semantic_properties={"name": "point"})
    b1.node("VarDecl", semantic_properties={"name": "point"})

    b2 = Builder()
    b2.node("RecordDecl", semantic_properties={"name": "point_tag"})
    b2.node("VarDecl", semantic_properties={"name": "origin"})

    b3 = Builder()
    b3.node("RecordDecl", semantic_properties={"name": "cfg"})
    b3.node("VarDecl", semantic_properties={"name": "cfg"}, macro_origin={"macro_name": "DECLARE_CFG"})

    b4 = Builder()
    b4.node("RecordDecl", semantic_properties={"name": "GPIO_TypeDef"})
    b4.node("VarDecl", semantic_properties={"name": "GPIO_TypeDef"})

    b5 = Builder()
    b5.node("VarDecl", semantic_properties={"name": "count"})
    b5.node("VarDecl", semantic_properties={"name": "count"})

    return _suite(
        "misra-c2012-rule-5-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_5_3() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("VarDecl", semantic_properties={"name": "count"})
    fn = b1.node("FunctionDecl", semantic_properties={"name": "f"})
    compound = b1.node("CompoundStmt", parent=fn)
    b1.node("VarDecl", parent=compound, semantic_properties={"name": "count"})

    b2 = Builder()
    b2.node("VarDecl", semantic_properties={"name": "count"})
    fn2 = b2.node("FunctionDecl", semantic_properties={"name": "f"})
    compound2 = b2.node("CompoundStmt", parent=fn2)
    b2.node("VarDecl", parent=compound2, semantic_properties={"name": "total"})

    b3 = Builder()
    b3.node("VarDecl", semantic_properties={"name": "count"})
    fn3 = b3.node("FunctionDecl", semantic_properties={"name": "f"})
    compound3 = b3.node("CompoundStmt", parent=fn3)
    b3.node(
        "VarDecl",
        parent=compound3,
        semantic_properties={"name": "count"},
        macro_origin={"macro_name": "DECLARE_LOCAL"},
    )

    b4 = Builder()
    fn4 = b4.node("FunctionDecl", semantic_properties={"name": "adc_read"})
    b4.node("ParmVarDecl", parent=fn4, semantic_properties={"name": "status"})
    compound4 = b4.node("CompoundStmt", parent=fn4)
    b4.node("VarDecl", parent=compound4, semantic_properties={"name": "status"})

    b5 = Builder()
    fn5 = b5.node("FunctionDecl", semantic_properties={"name": "f"})
    compound5 = b5.node("CompoundStmt", parent=fn5)
    b5.node("VarDecl", parent=compound5, semantic_properties={"name": "same_scope"})
    b5.node("VarDecl", parent=compound5, semantic_properties={"name": "same_scope"})

    return _suite(
        "misra-c2012-rule-5-3",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_2_7() -> RuleConformanceSuite:
    b1 = Builder()
    fn = b1.node("FunctionDecl", semantic_properties={"name": "log_event"})
    b1.node("ParmVarDecl", parent=fn, semantic_properties={"name": "code"})
    compound = b1.node("CompoundStmt", parent=fn)
    call = b1.node("CallExpr", parent=compound, semantic_properties={"callee": "record"})
    b1.node("IntegerLiteral", parent=call)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl", semantic_properties={"name": "log_event"})
    b2.node("ParmVarDecl", parent=fn2, semantic_properties={"name": "code"})
    compound2 = b2.node("CompoundStmt", parent=fn2)
    call2 = b2.node("CallExpr", parent=compound2, semantic_properties={"callee": "record"})
    b2.node("DeclRefExpr", parent=call2, semantic_properties={"name": "code"})

    b3 = Builder()
    fn3 = b3.node("FunctionDecl", semantic_properties={"name": "log_event"})
    b3.node(
        "ParmVarDecl",
        parent=fn3,
        semantic_properties={"name": "code"},
        macro_origin={"macro_name": "LOG_PARAM"},
    )
    compound3 = b3.node("CompoundStmt", parent=fn3)
    call3 = b3.node("CallExpr", parent=compound3, semantic_properties={"callee": "record"})
    b3.node("IntegerLiteral", parent=call3)

    b4 = Builder()
    fn4 = b4.node("FunctionDecl", semantic_properties={"name": "HAL_GPIO_Init"})
    b4.node("ParmVarDecl", parent=fn4, semantic_properties={"name": "GPIO_Pin"})
    compound4 = b4.node("CompoundStmt", parent=fn4)
    call4 = b4.node("CallExpr", parent=compound4, semantic_properties={"callee": "configure_default"})
    b4.node("IntegerLiteral", parent=call4)

    b5 = Builder()
    fn5 = b5.node("FunctionDecl", semantic_properties={"name": "log_event_prototype"})
    b5.node("ParmVarDecl", parent=fn5, semantic_properties={"name": "code"})

    return _suite(
        "misra-c2012-rule-2-7",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_13_1() -> RuleConformanceSuite:
    b1 = Builder()
    init_list = b1.node("InitListExpr")
    call = b1.node("CallExpr", parent=init_list, semantic_properties={"callee": "read_sensor"})
    _ = call
    b1.node("IntegerLiteral", parent=init_list)

    b2 = Builder()
    init_list2 = b2.node("InitListExpr")
    b2.node("IntegerLiteral", parent=init_list2)
    b2.node("IntegerLiteral", parent=init_list2)

    b3 = Builder()
    init_list3 = b3.node("InitListExpr")
    b3.node(
        "CallExpr",
        parent=init_list3,
        semantic_properties={"callee": "NEXT_VALUE"},
        macro_origin={"macro_name": "NEXT_VALUE"},
    )

    b4 = Builder()
    init_list4 = b4.node("InitListExpr")
    b4.node("CallExpr", parent=init_list4, semantic_properties={"callee": "HAL_GetTick"})
    b4.node("IntegerLiteral", parent=init_list4)

    b5 = Builder()
    init_list5 = b5.node("InitListExpr")
    nested = b5.node("InitListExpr", parent=init_list5)
    b5.node("IntegerLiteral", parent=nested)

    return _suite(
        "misra-c2012-rule-13-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_13_6() -> RuleConformanceSuite:
    b1 = Builder()
    sizeof1 = b1.node("UnaryOperator", semantic_properties={"opcode": "sizeof"})
    b1.node("UnaryOperator", parent=sizeof1, semantic_properties={"opcode": "++"})

    b2 = Builder()
    sizeof2 = b2.node("UnaryOperator", semantic_properties={"opcode": "sizeof"})
    b2.node("DeclRefExpr", parent=sizeof2, semantic_properties={"name": "buffer"})

    b3 = Builder()
    sizeof3 = b3.node("UnaryOperator", semantic_properties={"opcode": "sizeof"})
    b3.node(
        "UnaryOperator",
        parent=sizeof3,
        semantic_properties={"opcode": "++"},
        macro_origin={"macro_name": "NEXT_INDEX"},
    )

    b4 = Builder()
    sizeof4 = b4.node("UnaryOperator", semantic_properties={"opcode": "sizeof"})
    b4.node("BinaryOperator", parent=sizeof4, semantic_properties={"opcode": "+="})

    b5 = Builder()
    b5.node("UnaryOperator", semantic_properties={"opcode": "sizeof"})  # sizeof(TypeName): no operand child

    return _suite(
        "misra-c2012-rule-13-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_16_2() -> RuleConformanceSuite:
    b1 = Builder()
    switch1 = b1.node("SwitchStmt")
    body1 = b1.node("CompoundStmt", parent=switch1)
    nested1 = b1.node("CompoundStmt", parent=body1)
    b1.node("CaseStmt", parent=nested1)

    b2 = Builder()
    switch2 = b2.node("SwitchStmt")
    body2 = b2.node("CompoundStmt", parent=switch2)
    b2.node("CaseStmt", parent=body2)

    b3 = Builder()
    switch3 = b3.node("SwitchStmt")
    body3 = b3.node("CompoundStmt", parent=switch3)
    nested3 = b3.node("CompoundStmt", parent=body3)
    b3.node("CaseStmt", parent=nested3, macro_origin={"macro_name": "CASE_BLOCK"})

    b4 = Builder()
    switch4 = b4.node("SwitchStmt", semantic_properties={"name": "peripheral_state"})
    body4 = b4.node("CompoundStmt", parent=switch4)
    nested4 = b4.node("CompoundStmt", parent=body4)
    b4.node("DefaultStmt", parent=nested4)

    b5 = Builder()
    b5.node("CaseStmt")  # dangling: no parent at all

    return _suite(
        "misra-c2012-rule-16-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), True),
        ],
    )


def rule_16_5() -> RuleConformanceSuite:
    b1 = Builder()
    switch1 = b1.node("SwitchStmt")
    body1 = b1.node("CompoundStmt", parent=switch1)
    b1.node("CaseStmt", parent=body1)
    b1.node("DefaultStmt", parent=body1)
    b1.node("CaseStmt", parent=body1)

    b2 = Builder()
    switch2 = b2.node("SwitchStmt")
    body2 = b2.node("CompoundStmt", parent=switch2)
    b2.node("CaseStmt", parent=body2)
    b2.node("CaseStmt", parent=body2)
    b2.node("DefaultStmt", parent=body2)

    b3 = Builder()
    switch3 = b3.node("SwitchStmt")
    body3 = b3.node("CompoundStmt", parent=switch3)
    b3.node("CaseStmt", parent=body3)
    b3.node("DefaultStmt", parent=body3, macro_origin={"macro_name": "DEFAULT_CASE"})
    b3.node("CaseStmt", parent=body3)

    b4 = Builder()
    switch4 = b4.node("SwitchStmt")
    body4 = b4.node("CompoundStmt", parent=switch4)
    b4.node("CaseStmt", parent=body4, semantic_properties={"name": "ADC_IDLE"})
    b4.node("DefaultStmt", parent=body4)
    b4.node("CaseStmt", parent=body4, semantic_properties={"name": "ADC_BUSY"})

    b5 = Builder()
    switch5 = b5.node("SwitchStmt")
    body5 = b5.node("CompoundStmt", parent=switch5)
    b5.node("DefaultStmt", parent=body5)

    return _suite(
        "misra-c2012-rule-16-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_17_4() -> RuleConformanceSuite:
    b1 = Builder()
    fn1 = b1.node("FunctionDecl", essential_type="signed_int", semantic_properties={"name": "clamp"})
    compound1 = b1.node("CompoundStmt", parent=fn1)
    ifstmt1 = b1.node("IfStmt", parent=compound1)
    b1.node("DeclRefExpr", parent=ifstmt1)
    then1 = b1.node("CompoundStmt", parent=ifstmt1)
    ret1 = b1.node("ReturnStmt", parent=then1)
    b1.node("IntegerLiteral", parent=ret1)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl", essential_type="signed_int", semantic_properties={"name": "clamp"})
    compound2 = b2.node("CompoundStmt", parent=fn2)
    ret2 = b2.node("ReturnStmt", parent=compound2)
    b2.node("IntegerLiteral", parent=ret2)

    b3 = Builder()
    fn3 = b3.node("FunctionDecl", essential_type="signed_int", semantic_properties={"name": "clamp"})
    compound3 = b3.node("CompoundStmt", parent=fn3)
    b3.node("ReturnStmt", parent=compound3, macro_origin={"macro_name": "RETURN_EARLY"})

    b4 = Builder()
    fn4 = b4.node(
        "FunctionDecl", essential_type="unsigned_int", semantic_properties={"name": "HAL_Adc_Read"}
    )
    compound4 = b4.node("CompoundStmt", parent=fn4)
    b4.node("ReturnStmt", parent=compound4)

    b5 = Builder()
    fn5 = b5.node("FunctionDecl", essential_type="void", semantic_properties={"name": "reset"})
    compound5 = b5.node("CompoundStmt", parent=fn5)
    b5.node("ReturnStmt", parent=compound5)

    return _suite(
        "misra-c2012-rule-17-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_15_4() -> RuleConformanceSuite:
    b1 = Builder()
    fn1 = b1.node("FunctionDecl", semantic_properties={"name": "poll"})
    compound1 = b1.node("CompoundStmt", parent=fn1)
    loop1 = b1.node("WhileStmt", parent=compound1)
    b1.node("DeclRefExpr", parent=loop1)
    body1 = b1.node("CompoundStmt", parent=loop1)
    b1.node("BreakStmt", parent=body1)
    b1.node("BreakStmt", parent=body1)

    b2 = Builder()
    fn2 = b2.node("FunctionDecl", semantic_properties={"name": "poll"})
    compound2 = b2.node("CompoundStmt", parent=fn2)
    loop2 = b2.node("WhileStmt", parent=compound2)
    b2.node("DeclRefExpr", parent=loop2)
    body2 = b2.node("CompoundStmt", parent=loop2)
    b2.node("BreakStmt", parent=body2)

    b3 = Builder()
    fn3 = b3.node("FunctionDecl", semantic_properties={"name": "poll"})
    compound3 = b3.node("CompoundStmt", parent=fn3)
    loop3 = b3.node("WhileStmt", parent=compound3)
    b3.node("DeclRefExpr", parent=loop3)
    body3 = b3.node("CompoundStmt", parent=loop3)
    b3.node("BreakStmt", parent=body3)
    b3.node("BreakStmt", parent=body3, macro_origin={"macro_name": "ABORT_LOOP"})

    b4 = Builder()
    fn4 = b4.node("FunctionDecl", semantic_properties={"name": "adc_wait_ready"})
    compound4 = b4.node("CompoundStmt", parent=fn4)
    loop4 = b4.node("ForStmt", parent=compound4)
    b4.node("DeclRefExpr", parent=loop4)
    body4 = b4.node("CompoundStmt", parent=loop4)
    b4.node("BreakStmt", parent=body4)
    b4.node("BreakStmt", parent=body4)

    b5 = Builder()
    fn5 = b5.node("FunctionDecl", semantic_properties={"name": "poll"})
    compound5 = b5.node("CompoundStmt", parent=fn5)
    loop5 = b5.node("WhileStmt", parent=compound5)
    b5.node("DeclRefExpr", parent=loop5)
    body5 = b5.node("CompoundStmt", parent=loop5)
    if5a = b5.node("IfStmt", parent=body5)
    b5.node("BreakStmt", parent=if5a)
    if5b = b5.node("IfStmt", parent=body5)
    b5.node("BreakStmt", parent=if5b)
    if5c = b5.node("IfStmt", parent=body5)
    b5.node("BreakStmt", parent=if5c)

    return _suite(
        "misra-c2012-rule-15-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), True),
        ],
    )


def rule_5_8() -> RuleConformanceSuite:
    def _linkage(name: str, tus: list[str], node_kind: str = "VarDecl") -> dict:
        return {
            "symbols": {
                name: [
                    {
                        "translation_unit_id": tu,
                        "file_path": f"{tu}.c",
                        "storage_class": "external",
                        "has_body": True,
                        "type_spelling": "",
                        "node_kind": node_kind,
                    }
                    for tu in tus
                ]
            }
        }

    b1 = Builder()
    b1.node("VarDecl", semantic_properties={"name": "sensor_count"})
    linkage1 = _linkage("sensor_count", ["pos-1", "other"])

    b2 = Builder()
    b2.node("VarDecl", semantic_properties={"name": "sensor_count"})
    linkage2 = _linkage("sensor_count", ["neg-1"])

    b3 = Builder()
    b3.node("VarDecl", semantic_properties={"name": "sensor_count"}, macro_origin={"macro_name": "DEFINE_COUNTER"})
    linkage3 = _linkage("sensor_count", ["macro-1", "other"])

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "HAL_Init"})
    linkage4 = _linkage("HAL_Init", ["embedded-1", "other"], node_kind="FunctionDecl")

    b5 = Builder()
    b5.node("VarDecl", semantic_properties={"name": "sensor_count"})
    linkage5 = {"symbols": {}}

    return _suite(
        "misra-c2012-rule-5-8",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage1),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=linkage2),
            ConformanceCase("macro-1", "macro", b3.artifact(), True, cross_tu_linkage=linkage3),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True, cross_tu_linkage=linkage4),
            ConformanceCase("edge-1", "edge", b5.artifact(), False, cross_tu_linkage=linkage5),
        ],
    )


def rule_5_9() -> RuleConformanceSuite:
    def _occ(tu: str, storage: str, node_kind: str = "FunctionDecl") -> dict:
        return {
            "translation_unit_id": tu,
            "file_path": f"{tu}.c",
            "storage_class": storage,
            "has_body": True,
            "type_spelling": "",
            "node_kind": node_kind,
        }

    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "handle", "storage_class": "static"})
    linkage1 = {"symbols": {"handle": [_occ("pos-1", "static"), _occ("other", "static")]}}

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "handle", "storage_class": "static"})
    linkage2 = {"symbols": {"handle": [_occ("neg-1", "static")]}}

    b3 = Builder()
    b3.node(
        "FunctionDecl",
        semantic_properties={"name": "handle", "storage_class": "static"},
        macro_origin={"macro_name": "DEFINE_HANDLER"},
    )
    linkage3 = {"symbols": {"handle": [_occ("macro-1", "static"), _occ("other", "static")]}}

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "ADC_IRQHandler", "storage_class": "static"})
    linkage4 = {"symbols": {"ADC_IRQHandler": [_occ("embedded-1", "static"), _occ("other", "static")]}}

    b5 = Builder()
    b5.node("FunctionDecl", semantic_properties={"name": "handle", "storage_class": "static"})
    linkage5 = {
        "symbols": {
            "handle": [
                _occ("edge-1", "static"),
                _occ("other-a", "external"),
                _occ("other-b", "external"),
            ]
        }
    }

    return _suite(
        "misra-c2012-rule-5-9",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage1),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=linkage2),
            ConformanceCase("macro-1", "macro", b3.artifact(), True, cross_tu_linkage=linkage3),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True, cross_tu_linkage=linkage4),
            ConformanceCase("edge-1", "edge", b5.artifact(), False, cross_tu_linkage=linkage5),
        ],
    )


def rule_8_5() -> RuleConformanceSuite:
    def _occ(tu: str, has_body: bool) -> dict:
        return {
            "translation_unit_id": tu,
            "file_path": f"{tu}.c",
            "storage_class": "external",
            "has_body": has_body,
            "type_spelling": "",
            "node_kind": "VarDecl",
        }

    b1 = Builder()
    b1.node("VarDecl", semantic_properties={"name": "counter"})
    linkage1 = {"symbols": {"counter": [_occ("pos-1", False), _occ("other", False)]}}

    b2 = Builder()
    b2.node("VarDecl", semantic_properties={"name": "counter"})
    linkage2 = {"symbols": {"counter": [_occ("neg-1", False)]}}

    b3 = Builder()
    b3.node("VarDecl", semantic_properties={"name": "counter"}, macro_origin={"macro_name": "DECLARE_EXTERN"})
    linkage3 = {"symbols": {"counter": [_occ("macro-1", False), _occ("other", False)]}}

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "HAL_Delay"})
    linkage4 = {
        "symbols": {
            "HAL_Delay": [
                {
                    "translation_unit_id": "embedded-1",
                    "file_path": "embedded-1.c",
                    "storage_class": "external",
                    "has_body": False,
                    "type_spelling": "",
                    "node_kind": "FunctionDecl",
                },
                {
                    "translation_unit_id": "other",
                    "file_path": "other.c",
                    "storage_class": "external",
                    "has_body": False,
                    "type_spelling": "",
                    "node_kind": "FunctionDecl",
                },
            ]
        }
    }

    b5 = Builder()
    b5.node("VarDecl", semantic_properties={"name": "counter"})
    linkage5 = {"symbols": {"counter": [_occ("edge-1", False), _occ("other", True)]}}

    return _suite(
        "misra-c2012-rule-8-5",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True, cross_tu_linkage=linkage1),
            ConformanceCase("neg-1", "negative", b2.artifact(), False, cross_tu_linkage=linkage2),
            ConformanceCase("macro-1", "macro", b3.artifact(), True, cross_tu_linkage=linkage3),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True, cross_tu_linkage=linkage4),
            ConformanceCase("edge-1", "edge", b5.artifact(), False, cross_tu_linkage=linkage5),
        ],
    )


def rule_8_8() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})
    b1.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "external"})

    b2 = Builder()
    b2.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})
    b2.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})

    b3 = Builder()
    b3.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})
    b3.node(
        "FunctionDecl",
        semantic_properties={"name": "helper", "storage_class": "external"},
        macro_origin={"macro_name": "DEFINE_HELPER"},
    )

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "Error_Handler", "storage_class": "static"})
    b4.node("FunctionDecl", semantic_properties={"name": "Error_Handler", "storage_class": "external"})

    b5 = Builder()
    b5.node("FunctionDecl", semantic_properties={"name": "helper", "storage_class": "static"})

    return _suite(
        "misra-c2012-rule-8-8",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_2_5() -> RuleConformanceSuite:
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "UNUSED_MAX", "value": "10", "is_function_like": False, "range": {}}],
            "macro_expansions": [],
        },
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "MAX_RETRIES", "value": "3", "is_function_like": False, "range": {}}],
            "macro_expansions": [{"name": "MAX_RETRIES", "range": {}}],
        },
    }
    macro_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "SQUARE", "value": "((x) * (x))", "is_function_like": True, "range": {}}],
            "macro_expansions": [],
        },
    }
    embedded_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "GPIO_PIN_13", "value": "13", "is_function_like": False, "range": {}}],
            "macro_expansions": [],
        },
    }
    edge_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {},
    }
    return _suite(
        "misra-c2012-rule-2-5",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
            ConformanceCase("macro-1", "macro", macro_artifact, True),
            ConformanceCase("embedded-1", "embedded", embedded_artifact, True),
            ConformanceCase("edge-1", "edge", edge_artifact, False),
        ],
    )


def rule_5_4() -> RuleConformanceSuite:
    prefix = "SENSOR_TIMEOUT_THRESHOLD_MODUL"  # 30 chars, collides once truncated to 31
    positive_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [
                {"name": prefix + "EA", "value": "100", "is_function_like": False, "range": {}},
                {"name": prefix + "EB", "value": "200", "is_function_like": False, "range": {}},
            ]
        },
    }
    negative_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [
                {"name": "SENSOR_TIMEOUT_MS", "value": "100", "is_function_like": False, "range": {}}
            ]
        },
    }
    macro_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [
                {"name": prefix + "EA", "value": "100", "is_function_like": False, "range": {}},
                {"name": prefix + "EB", "value": "200", "is_function_like": False, "range": {}},
                {"name": prefix + "EC", "value": "300", "is_function_like": False, "range": {}},
            ]
        },
    }
    embedded_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [
                {"name": prefix + "ULE_A", "value": "1", "is_function_like": False, "range": {}},
                {"name": prefix + "ULE_B", "value": "2", "is_function_like": False, "range": {}},
            ]
        },
    }
    edge_artifact = {
        "file_path": "demo.c",
        "nodes": [],
        "diagnostics": [],
        "preprocessor": {
            "macro_definitions": [{"name": "ONLY_ONE", "value": "1", "is_function_like": False, "range": {}}]
        },
    }
    return _suite(
        "misra-c2012-rule-5-4",
        [
            ConformanceCase("pos-1", "positive", positive_artifact, True),
            ConformanceCase("neg-1", "negative", negative_artifact, False),
            ConformanceCase("macro-1", "macro", macro_artifact, True),
            ConformanceCase("embedded-1", "embedded", embedded_artifact, True),
            ConformanceCase("edge-1", "edge", edge_artifact, False),
        ],
    )


def rule_21_2() -> RuleConformanceSuite:
    b1 = Builder()
    b1.node("VarDecl", semantic_properties={"name": "_Reserved"})

    b2 = Builder()
    b2.node("VarDecl", semantic_properties={"name": "app_counter"})

    b3 = Builder()
    b3.node("VarDecl", semantic_properties={"name": "_Reserved"}, macro_origin={"macro_name": "DECLARE_RESERVED"})

    b4 = Builder()
    b4.node("FunctionDecl", semantic_properties={"name": "__HAL_Init"})

    b5 = Builder()
    b5.node("VarDecl", semantic_properties={"name": "_lowercase"})

    return _suite(
        "misra-c2012-rule-21-2",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_7_4() -> RuleConformanceSuite:
    b1 = Builder()
    var1 = b1.node("VarDecl", qualifiers=[], semantic_properties={"name": "greeting"})
    b1.node("StringLiteral", parent=var1)

    b2 = Builder()
    var2 = b2.node("VarDecl", qualifiers=["const"], semantic_properties={"name": "greeting"})
    b2.node("StringLiteral", parent=var2)

    b3 = Builder()
    var3 = b3.node("VarDecl", qualifiers=[], semantic_properties={"name": "greeting"})
    b3.node("StringLiteral", parent=var3, macro_origin={"macro_name": "MSG"})

    b4 = Builder()
    var4 = b4.node("VarDecl", qualifiers=[], semantic_properties={"name": "error_msg"})
    b4.node("StringLiteral", parent=var4, semantic_properties={"value": "UART TX failed"})

    b5 = Builder()
    var5 = b5.node("VarDecl", qualifiers=[], semantic_properties={"name": "count"})
    b5.node("IntegerLiteral", parent=var5)

    return _suite(
        "misra-c2012-rule-7-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_11_1() -> RuleConformanceSuite:
    b1 = Builder()
    cast1 = b1.node("CStyleCastExpr", type_information={"spelling": "void (*)(int32_t)"})
    b1.node("DeclRefExpr", parent=cast1, type_information={"spelling": "void *"})

    b2 = Builder()
    cast2 = b2.node("CStyleCastExpr", type_information={"spelling": "void (*)(int32_t)"})
    b2.node("DeclRefExpr", parent=cast2, type_information={"spelling": "void (*)(int32_t)"})

    b3 = Builder()
    cast3 = b3.node(
        "CStyleCastExpr",
        type_information={"spelling": "void (*)(int32_t)"},
        macro_origin={"macro_name": "AS_HANDLER"},
    )
    b3.node("DeclRefExpr", parent=cast3, type_information={"spelling": "void *"})

    b4 = Builder()
    cast4 = b4.node("CStyleCastExpr", type_information={"spelling": "void (*)(void)"})
    b4.node("DeclRefExpr", parent=cast4, type_information={"spelling": "uint32_t"})

    b5 = Builder()
    b5.node("CStyleCastExpr", type_information={"spelling": "void (*)(void)"})  # no operand child

    return _suite(
        "misra-c2012-rule-11-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_11_6() -> RuleConformanceSuite:
    b1 = Builder()
    cast1 = b1.node("CStyleCastExpr", type_information={"is_pointer": False}, essential_type="unsigned_int")
    b1.node("DeclRefExpr", parent=cast1, type_information={"is_pointer": True, "pointee_type": "void"})

    b2 = Builder()
    cast2 = b2.node(
        "CStyleCastExpr", type_information={"is_pointer": True, "pointee_type": "uint8_t"}
    )
    b2.node("DeclRefExpr", parent=cast2, type_information={"is_pointer": True, "pointee_type": "void"})

    b3 = Builder()
    cast3 = b3.node(
        "CStyleCastExpr",
        type_information={"is_pointer": False},
        essential_type="unsigned_int",
        macro_origin={"macro_name": "AS_ADDRESS"},
    )
    b3.node("DeclRefExpr", parent=cast3, type_information={"is_pointer": True, "pointee_type": "void"})

    b4 = Builder()
    cast4 = b4.node("CStyleCastExpr", type_information={"is_pointer": False}, essential_type="unsigned_long")
    b4.node("DeclRefExpr", parent=cast4, type_information={"is_pointer": True, "pointee_type": "const void"})

    b5 = Builder()
    cast5 = b5.node("CStyleCastExpr", type_information={"is_pointer": True, "pointee_type": "void"})
    b5.node("DeclRefExpr", parent=cast5, type_information={"is_pointer": True, "pointee_type": "void"})

    return _suite(
        "misra-c2012-rule-11-6",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_18_3() -> RuleConformanceSuite:
    b1 = Builder()
    op1 = b1.node("BinaryOperator", semantic_properties={"opcode": "<"})
    b1.node("DeclRefExpr", parent=op1, type_information={"is_pointer": True, "pointee_type": "uint8_t"})
    b1.node("DeclRefExpr", parent=op1, type_information={"is_pointer": True, "pointee_type": "uint16_t"})

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "<"})
    b2.node("DeclRefExpr", parent=op2, type_information={"is_pointer": True, "pointee_type": "uint8_t"})
    b2.node("DeclRefExpr", parent=op2, type_information={"is_pointer": True, "pointee_type": "uint8_t"})

    b3 = Builder()
    op3 = b3.node("BinaryOperator", semantic_properties={"opcode": "<"}, macro_origin={"macro_name": "IS_BEFORE"})
    b3.node("DeclRefExpr", parent=op3, type_information={"is_pointer": True, "pointee_type": "uint8_t"})
    b3.node("DeclRefExpr", parent=op3, type_information={"is_pointer": True, "pointee_type": "uint16_t"})

    b4 = Builder()
    op4 = b4.node("BinaryOperator", semantic_properties={"opcode": "<"})
    b4.node("DeclRefExpr", parent=op4, type_information={"is_pointer": True, "pointee_type": "uart_buffer_t"})
    b4.node("DeclRefExpr", parent=op4, type_information={"is_pointer": True, "pointee_type": "spi_buffer_t"})

    b5 = Builder()
    op5 = b5.node("BinaryOperator", semantic_properties={"opcode": "<="})
    b5.node("DeclRefExpr", parent=op5, type_information={"is_pointer": True, "pointee_type": "uint8_t"})
    b5.node("IntegerLiteral", parent=op5, type_information={"is_pointer": False})

    return _suite(
        "misra-c2012-rule-18-3",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_18_4() -> RuleConformanceSuite:
    b1 = Builder()
    op1 = b1.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b1.node("DeclRefExpr", parent=op1, type_information={"is_pointer": True})
    b1.node("IntegerLiteral", parent=op1, type_information={"is_pointer": False})

    b2 = Builder()
    op2 = b2.node("BinaryOperator", semantic_properties={"opcode": "+"})
    b2.node("IntegerLiteral", parent=op2, type_information={"is_pointer": False})
    b2.node("IntegerLiteral", parent=op2, type_information={"is_pointer": False})

    b3 = Builder()
    op3 = b3.node("BinaryOperator", semantic_properties={"opcode": "+"}, macro_origin={"macro_name": "ADVANCE"})
    b3.node("DeclRefExpr", parent=op3, type_information={"is_pointer": True})
    b3.node("IntegerLiteral", parent=op3, type_information={"is_pointer": False})

    b4 = Builder()
    op4 = b4.node("BinaryOperator", semantic_properties={"opcode": "-="})
    b4.node("DeclRefExpr", parent=op4, type_information={"is_pointer": True})
    b4.node("IntegerLiteral", parent=op4, type_information={"is_pointer": False})

    b5 = Builder()
    op5 = b5.node("BinaryOperator", semantic_properties={"opcode": "*"})
    b5.node("DeclRefExpr", parent=op5, type_information={"is_pointer": True})
    b5.node("IntegerLiteral", parent=op5, type_information={"is_pointer": False})

    return _suite(
        "misra-c2012-rule-18-4",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def _memcpy_case(b: Builder, callee: str, target_name: str = "buffer") -> None:
    fn = b.node("FunctionDecl", semantic_properties={"name": "copy_block"})
    compound = b.node("CompoundStmt", parent=fn)

    p_decl = b.node("VarDecl", parent=compound, type_information={"is_pointer": True}, semantic_properties={"name": "p"})
    addr_p = b.node("UnaryOperator", parent=p_decl, semantic_properties={"opcode": "&"})
    b.node("DeclRefExpr", parent=addr_p, semantic_properties={"name": "buffer"})

    q_decl = b.node("VarDecl", parent=compound, type_information={"is_pointer": True}, semantic_properties={"name": "q"})
    addr_q = b.node("UnaryOperator", parent=q_decl, semantic_properties={"opcode": "&"})
    b.node("DeclRefExpr", parent=addr_q, semantic_properties={"name": target_name})

    call = b.node("CallExpr", parent=compound, semantic_properties={"callee": callee})
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "p"})
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "q"})
    b.node("IntegerLiteral", parent=call)


def rule_19_1() -> RuleConformanceSuite:
    b1 = Builder()
    _memcpy_case(b1, "memcpy", target_name="buffer")

    b2 = Builder()
    _memcpy_case(b2, "memcpy", target_name="other_buffer")

    b3 = Builder()
    fn3 = b3.node("FunctionDecl", semantic_properties={"name": "copy_block"})
    compound3 = b3.node("CompoundStmt", parent=fn3)
    p_decl3 = b3.node(
        "VarDecl", parent=compound3, type_information={"is_pointer": True}, semantic_properties={"name": "p"}
    )
    addr_p3 = b3.node("UnaryOperator", parent=p_decl3, semantic_properties={"opcode": "&"})
    b3.node("DeclRefExpr", parent=addr_p3, semantic_properties={"name": "buffer"})
    q_decl3 = b3.node(
        "VarDecl", parent=compound3, type_information={"is_pointer": True}, semantic_properties={"name": "q"}
    )
    addr_q3 = b3.node("UnaryOperator", parent=q_decl3, semantic_properties={"opcode": "&"})
    b3.node("DeclRefExpr", parent=addr_q3, semantic_properties={"name": "buffer"})
    call3 = b3.node(
        "CallExpr",
        parent=compound3,
        semantic_properties={"callee": "memcpy"},
        macro_origin={"macro_name": "COPY_BLOCK"},
    )
    b3.node("DeclRefExpr", parent=call3, semantic_properties={"name": "p"})
    b3.node("DeclRefExpr", parent=call3, semantic_properties={"name": "q"})
    b3.node("IntegerLiteral", parent=call3)

    b4 = Builder()
    _memcpy_case(b4, "strcpy", target_name="buffer")

    b5 = Builder()
    _memcpy_case(b5, "memmove", target_name="buffer")

    return _suite(
        "misra-c2012-rule-19-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def rule_2_1() -> RuleConformanceSuite:
    # positive: a statement placed after an unconditional return is dead code.
    b1 = Builder()
    fn1 = b1.node("FunctionDecl", semantic_properties={"name": "compute"})
    body1 = b1.node("CompoundStmt", parent=fn1)
    b1.node("ReturnStmt", parent=body1, line=1)
    b1.node("VarDecl", parent=body1, semantic_properties={"name": "unused"}, line=2)

    # negative: straight-line sequential code with a single reachable return.
    b2 = Builder()
    fn2 = b2.node("FunctionDecl", semantic_properties={"name": "compute"})
    body2 = b2.node("CompoundStmt", parent=fn2)
    b2.node("VarDecl", parent=body2, semantic_properties={"name": "result"}, line=1)
    b2.node("ReturnStmt", parent=body2, line=2)

    # macro: the dead statement is expanded from a logging macro, but is
    # still structurally unreachable because it follows an unconditional return.
    b3 = Builder()
    fn3 = b3.node("FunctionDecl", semantic_properties={"name": "compute"})
    body3 = b3.node("CompoundStmt", parent=fn3)
    b3.node("ReturnStmt", parent=body3, line=1)
    b3.node(
        "CallExpr",
        parent=body3,
        semantic_properties={"callee": "LOG_TRACE"},
        macro_origin={"macro_name": "LOG_TRACE"},
        line=2,
    )

    # embedded: HAL-style pattern where both branches of an if/else return,
    # making any cleanup statement placed after the if unreachable.
    b4 = Builder()
    fn4 = b4.node("FunctionDecl", semantic_properties={"name": "HAL_GPIO_Init"})
    body4 = b4.node("CompoundStmt", parent=fn4)
    if_stmt4 = b4.node("IfStmt", parent=body4, line=1)
    b4.node("BinaryOperator", parent=if_stmt4, semantic_properties={"opcode": "=="}, line=1)
    then4 = b4.node("CompoundStmt", parent=if_stmt4)
    b4.node("ReturnStmt", parent=then4, line=2)
    else4 = b4.node("CompoundStmt", parent=if_stmt4)
    b4.node("ReturnStmt", parent=else4, line=3)
    b4.node("VarDecl", parent=body4, semantic_properties={"name": "status"}, line=4)

    # edge: an empty function body has no statements at all, so there is
    # nothing that could be classified as unreachable.
    b5 = Builder()
    fn5 = b5.node("FunctionDecl", semantic_properties={"name": "noop"})
    b5.node("CompoundStmt", parent=fn5)

    return _suite(
        "misra-c2012-rule-2-1",
        [
            ConformanceCase("pos-1", "positive", b1.artifact(), True),
            ConformanceCase("neg-1", "negative", b2.artifact(), False),
            ConformanceCase("macro-1", "macro", b3.artifact(), True),
            ConformanceCase("embedded-1", "embedded", b4.artifact(), True),
            ConformanceCase("edge-1", "edge", b5.artifact(), False),
        ],
    )


def build_all_suites() -> list[RuleConformanceSuite]:
    builders = [
        rule_10_1, rule_10_2, rule_10_3, rule_10_4, rule_10_5, rule_10_7,
        rule_8_2, rule_8_4, rule_8_6, rule_8_14,
        rule_11_4, rule_11_5, rule_11_8, rule_11_9, rule_18_2,
        rule_15_1, rule_15_5, rule_15_6, rule_16_3, rule_16_4, rule_16_6,
        rule_20_4, rule_20_7, rule_20_14, rule_21_1,
        rule_12_3, rule_13_4, rule_13_5, rule_14_4,
        rule_9_1, rule_2_2,
        rule_8_9, rule_18_6,
        rule_5_1, rule_8_7, rule_8_10,
        # --- Phase 5 ---------------------------------------------------
        rule_5_2, rule_5_3, rule_2_7,
        rule_13_1, rule_13_6,
        rule_16_2, rule_16_5, rule_17_4, rule_15_4,
        rule_5_8, rule_5_9, rule_8_5, rule_8_8,
        rule_2_5, rule_5_4, rule_21_2,
        rule_7_4, rule_11_1, rule_11_6,
        rule_18_3, rule_18_4, rule_19_1,
        rule_2_1,
        # --- Phase 6 ---------------------------------------------------
        *PHASE6_SUITE_BUILDERS,
        # --- Phase 6.2 ---------------------------------------------------
        *PHASE62_SUITE_BUILDERS,
        # --- Phase 6.3 ---------------------------------------------------
        *PHASE63_SUITE_BUILDERS,
        # --- Phase 6.4 ---------------------------------------------------
        *PHASE64_SUITE_BUILDERS,
        # --- Phase 6.5 ---------------------------------------------------
        *PHASE65_SUITE_BUILDERS,
        # --- Phase 7.1 ---------------------------------------------------
        *PHASE71_SUITE_BUILDERS,
    ]
    return [builder() for builder in builders]
