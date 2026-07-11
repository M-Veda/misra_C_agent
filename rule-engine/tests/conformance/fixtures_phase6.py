"""Phase 6 conformance fixtures — five case kinds per newly shipped rule.

Convention (matches `fixtures.py` throughout the harness):
  * `positive` case → `expects_violation=True`  (non-compliant AST)
  * `negative` case → `expects_violation=False` (compliant AST)
"""

from conformance.ast_builders import Builder
from misra_platform_rules.conformance import ConformanceCase, RuleConformanceSuite


def _suite(rule_id: str, cases: list[ConformanceCase]) -> RuleConformanceSuite:
    return RuleConformanceSuite(rule_id=rule_id, cases=cases)


def rule_2_3() -> RuleConformanceSuite:
    compliant = Builder()
    compliant.node("TypedefDecl", semantic_properties={"name": "speed_kph_t"})
    compliant.node("VarDecl", semantic_properties={"name": "current", "type_name": "speed_kph_t"})
    non_compliant = Builder()
    non_compliant.node("TypedefDecl", semantic_properties={"name": "unused_t"})
    return _suite(
        "misra-c2012-rule-2-3",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_2_4() -> RuleConformanceSuite:
    compliant = Builder()
    compliant.node("RecordDecl", semantic_properties={"name": "point_tag"})
    compliant.node("VarDecl", semantic_properties={"name": "origin", "type_name": "point_tag"})
    non_compliant = Builder()
    non_compliant.node("RecordDecl", semantic_properties={"name": "unused_tag"})
    return _suite(
        "misra-c2012-rule-2-4",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_5_5() -> RuleConformanceSuite:
    non_compliant = {
        "file_path": "demo.c",
        "nodes": [{"node_id": "v1", "node_kind": "VarDecl", "parent_id": "", "children_ids": [],
                   "semantic_properties": {"name": "MAX_SPEED"}, "source_range": {"line_start": 2}}],
        "diagnostics": [],
        "preprocessor": {"macro_definitions": [{"name": "MAX_SPEED", "value": "250"}]},
    }
    compliant = {
        "file_path": "demo.c",
        "nodes": [{"node_id": "v1", "node_kind": "VarDecl", "parent_id": "", "children_ids": [],
                   "semantic_properties": {"name": "current_speed"}, "source_range": {"line_start": 2}}],
        "diagnostics": [],
        "preprocessor": {"macro_definitions": [{"name": "MAX_SPEED", "value": "250"}]},
    }
    return _suite(
        "misra-c2012-rule-5-5",
        [
            ConformanceCase("pos-1", "positive", non_compliant, True),
            ConformanceCase("neg-1", "negative", compliant, False),
            ConformanceCase("macro-1", "macro", non_compliant, True),
            ConformanceCase("embedded-1", "embedded", non_compliant, True),
            ConformanceCase("edge-1", "edge", {"file_path": "demo.c", "nodes": [], "diagnostics": [], "preprocessor": {}}, False),
        ],
    )


def rule_5_6() -> RuleConformanceSuite:
    compliant = Builder()
    compliant.node("TypedefDecl", semantic_properties={"name": "speed_kph_t"})
    compliant.node("VarDecl", semantic_properties={"name": "current", "type_name": "speed_kph_t"})
    non_compliant = Builder()
    non_compliant.node("TypedefDecl", semantic_properties={"name": "speed_kph_t"})
    non_compliant.node("VarDecl", semantic_properties={"name": "speed_kph_t"})
    return _suite(
        "misra-c2012-rule-5-6",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_5_7() -> RuleConformanceSuite:
    compliant = Builder()
    compliant.node("RecordDecl", semantic_properties={"name": "point_tag"})
    compliant.node("VarDecl", semantic_properties={"name": "origin", "type_name": "point_tag"})
    non_compliant = Builder()
    non_compliant.node("RecordDecl", semantic_properties={"name": "point_tag"})
    non_compliant.node("VarDecl", semantic_properties={"name": "point_tag"})
    return _suite(
        "misra-c2012-rule-5-7",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_8_1() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("VarDecl", semantic_properties={"name": "counter", "implicit_type": True})
    compliant = Builder()
    compliant.node("VarDecl", semantic_properties={"name": "counter"})
    return _suite(
        "misra-c2012-rule-8-1",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_17_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    call = non_compliant.node("CallExpr", parent=body, semantic_properties={"callee": "compute", "implicit_declaration": True})
    non_compliant.node("IntegerLiteral", parent=call)
    compliant = Builder()
    compliant.node("FunctionDecl", semantic_properties={"name": "compute"})
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    call2 = compliant.node("CallExpr", parent=body2, semantic_properties={"callee": "compute"})
    compliant.node("IntegerLiteral", parent=call2)
    return _suite(
        "misra-c2012-rule-17-3",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_17_6() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "process"})
    non_compliant.node("ParmVarDecl", parent=fn, semantic_properties={"name": "buffer", "is_array": True, "array_static": True})
    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "process"})
    compliant.node("ParmVarDecl", parent=fn2, semantic_properties={"name": "buffer", "is_array": True})
    return _suite(
        "misra-c2012-rule-17-6",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_18_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    rec = non_compliant.node("RecordDecl", semantic_properties={"name": "frame_tag"})
    non_compliant.node("FieldDecl", parent=rec, semantic_properties={"name": "payload", "is_flexible_array_member": True})
    compliant = Builder()
    rec2 = compliant.node("RecordDecl", semantic_properties={"name": "frame_tag"})
    compliant.node("FieldDecl", parent=rec2, semantic_properties={"name": "length"})
    return _suite(
        "misra-c2012-rule-18-7",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_19_2() -> RuleConformanceSuite:
    non_compliant = Builder()
    non_compliant.node("RecordDecl", semantic_properties={"name": "value_u", "record_kind": "union"})
    compliant = Builder()
    compliant.node("RecordDecl", semantic_properties={"name": "point_tag", "record_kind": "struct"})
    return _suite(
        "misra-c2012-rule-19-2",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def _goto_fixtures() -> tuple[Builder, Builder]:
    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body = compliant.node("CompoundStmt", parent=fn)
    if_stmt = compliant.node("IfStmt", parent=body)
    compliant.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "<"})
    then_b = compliant.node("CompoundStmt", parent=if_stmt)
    compliant.node("GotoStmt", parent=then_b, semantic_properties={"target_label": "cleanup"})
    compliant.node("LabelStmt", parent=body, semantic_properties={"name": "cleanup"})

    non_compliant = Builder()
    fn2 = non_compliant.node("FunctionDecl", semantic_properties={"name": "f"})
    body2 = non_compliant.node("CompoundStmt", parent=fn2)
    non_compliant.node("GotoStmt", parent=body2, semantic_properties={"target_label": "inner"})
    if2 = non_compliant.node("IfStmt", parent=body2)
    non_compliant.node("IntegerLiteral", parent=if2)
    inner = non_compliant.node("CompoundStmt", parent=if2)
    non_compliant.node("LabelStmt", parent=inner, semantic_properties={"name": "inner"})
    return compliant, non_compliant


def rule_15_2() -> RuleConformanceSuite:
    compliant, non_compliant = _goto_fixtures()
    return _suite(
        "misra-c2012-rule-15-2",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_15_3() -> RuleConformanceSuite:
    compliant, non_compliant = _goto_fixtures()
    return _suite(
        "misra-c2012-rule-15-3",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_15_7() -> RuleConformanceSuite:
    non_compliant = Builder()
    fn = non_compliant.node("FunctionDecl", semantic_properties={"name": "dispatch"})
    body = non_compliant.node("CompoundStmt", parent=fn)
    outer = non_compliant.node("IfStmt", parent=body)
    non_compliant.node("BinaryOperator", parent=outer, semantic_properties={"opcode": "=="})
    then_b = non_compliant.node("CompoundStmt", parent=outer)
    non_compliant.node("ReturnStmt", parent=then_b)
    elif_b = non_compliant.node("IfStmt", parent=outer)
    non_compliant.node("BinaryOperator", parent=elif_b, semantic_properties={"opcode": "=="})
    elif_then = non_compliant.node("CompoundStmt", parent=elif_b)
    non_compliant.node("ReturnStmt", parent=elif_then)

    compliant = Builder()
    fn2 = compliant.node("FunctionDecl", semantic_properties={"name": "dispatch"})
    body2 = compliant.node("CompoundStmt", parent=fn2)
    outer2 = compliant.node("IfStmt", parent=body2)
    compliant.node("BinaryOperator", parent=outer2, semantic_properties={"opcode": "=="})
    then2 = compliant.node("CompoundStmt", parent=outer2)
    compliant.node("ReturnStmt", parent=then2)
    elif2 = compliant.node("IfStmt", parent=outer2)
    compliant.node("BinaryOperator", parent=elif2, semantic_properties={"opcode": "=="})
    elif_then2 = compliant.node("CompoundStmt", parent=elif2)
    compliant.node("ReturnStmt", parent=elif_then2)
    else2 = compliant.node("CompoundStmt", parent=outer2)
    compliant.node("ReturnStmt", parent=else2)

    return _suite(
        "misra-c2012-rule-15-7",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_14_2() -> RuleConformanceSuite:
    compliant = Builder()
    fn = compliant.node("FunctionDecl", semantic_properties={"name": "loop"})
    body = compliant.node("CompoundStmt", parent=fn)
    for_stmt = compliant.node("ForStmt", parent=body)
    compliant.node("VarDecl", parent=for_stmt, semantic_properties={"name": "i"})
    compliant.node("BinaryOperator", parent=for_stmt, semantic_properties={"opcode": "<"})
    compliant.node("UnaryOperator", parent=for_stmt, semantic_properties={"opcode": "++"})
    compliant.node("CompoundStmt", parent=for_stmt)

    non_compliant = Builder()
    fn2 = non_compliant.node("FunctionDecl", semantic_properties={"name": "loop"})
    body2 = non_compliant.node("CompoundStmt", parent=fn2)
    for2 = non_compliant.node("ForStmt", parent=body2)
    non_compliant.node("VarDecl", parent=for2, semantic_properties={"name": "i"})
    non_compliant.node("BinaryOperator", parent=for2, semantic_properties={"opcode": "<"})
    non_compliant.node("CompoundStmt", parent=for2)

    return _suite(
        "misra-c2012-rule-14-2",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_9_3() -> RuleConformanceSuite:
    non_compliant = Builder()
    init = non_compliant.node("InitListExpr", semantic_properties={"is_array_initializer": True})
    non_compliant.node("IntegerLiteral", parent=init, semantic_properties={"designator_index": 0})
    non_compliant.node("IntegerLiteral", parent=init, semantic_properties={"designator_index": 0})

    compliant = Builder()
    init2 = compliant.node("InitListExpr", semantic_properties={"is_array_initializer": True})
    compliant.node("IntegerLiteral", parent=init2, semantic_properties={"designator_index": 0})
    compliant.node("IntegerLiteral", parent=init2, semantic_properties={"designator_index": 1})

    return _suite(
        "misra-c2012-rule-9-3",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


def rule_9_5() -> RuleConformanceSuite:
    non_compliant = Builder()
    init = non_compliant.node("InitListExpr", semantic_properties={"is_array_initializer": True})
    non_compliant.node("IntegerLiteral", parent=init, semantic_properties={"designator_index": 0})
    non_compliant.node("IntegerLiteral", parent=init)

    compliant = Builder()
    init2 = compliant.node("InitListExpr", semantic_properties={"is_array_initializer": True})
    compliant.node("IntegerLiteral", parent=init2, semantic_properties={"designator_index": 0})
    compliant.node("IntegerLiteral", parent=init2, semantic_properties={"designator_index": 1})

    return _suite(
        "misra-c2012-rule-9-5",
        [
            ConformanceCase("pos-1", "positive", non_compliant.artifact(), True),
            ConformanceCase("neg-1", "negative", compliant.artifact(), False),
            ConformanceCase("macro-1", "macro", non_compliant.artifact(), True),
            ConformanceCase("embedded-1", "embedded", non_compliant.artifact(), True),
            ConformanceCase("edge-1", "edge", Builder().artifact(), False),
        ],
    )


PHASE6_SUITE_BUILDERS = [
    rule_2_3, rule_2_4, rule_5_5, rule_5_6, rule_5_7, rule_8_1,
    rule_17_3, rule_17_6, rule_18_7, rule_19_2,
    rule_15_2, rule_15_3, rule_15_7, rule_14_2,
    rule_9_3, rule_9_5,
]
