from misra_platform_rules.analyzers import (
    CastAnalyzer,
    CFGBuilder,
    DataFlowEngine,
    EssentialTypeAnalyzer,
    ExpressionClassifier,
    LinkageIndex,
    MacroAnalyzer,
    PointerAnalyzer,
    QualifierAnalyzer,
    SymbolIndex,
)
from misra_platform_rules.ast_graph import AstGraph


def node(node_id, kind, parent="", children=None, **kwargs):
    payload = {
        "node_id": node_id,
        "node_kind": kind,
        "parent_id": parent,
        "children_ids": children or [],
        "source_range": kwargs.pop("source_range", {"line_start": 1, "line_end": 1, "column_start": 1}),
        "type_information": kwargs.pop("type_information", {}),
        "qualifiers": kwargs.pop("qualifiers", []),
        "essential_type": kwargs.pop("essential_type", "unknown"),
        "macro_origin": kwargs.pop("macro_origin", {}),
        "semantic_properties": kwargs.pop("semantic_properties", {}),
    }
    payload.update(kwargs)
    return payload


def test_essential_type_analyzer_narrowing_and_pairs():
    analyzer = EssentialTypeAnalyzer()
    assert analyzer.is_narrowing("unsigned_int", "unsigned_char")
    assert not analyzer.is_narrowing("unsigned_char", "unsigned_int")
    assert analyzer.is_inappropriate_operand_pair("boolean", "signed_int")
    assert analyzer.category("unsigned_short") == "unsigned"


def test_cast_analyzer_removed_qualifiers_and_narrowing():
    analyzer = CastAnalyzer()
    cast_node = node(
        "c1",
        "CStyleCastExpr",
        essential_type="unsigned_char",
        semantic_properties={"removes_qualifier": True, "removed_qualifiers": ["const"]},
    )
    operand = node("c2", "DeclRefExpr", essential_type="unsigned_int")
    assert analyzer.removed_qualifiers(cast_node) == ["const"]
    assert analyzer.narrows(cast_node, operand)


def test_pointer_analyzer_incompatible_assignment():
    analyzer = PointerAnalyzer()
    lhs = node("p1", "VarDecl", type_information={"is_pointer": True, "pointee_type": "int"})
    rhs = node("p2", "VarDecl", type_information={"is_pointer": True, "pointee_type": "float"})
    assert analyzer.is_incompatible_pointer_assignment(lhs, rhs)


def test_qualifier_analyzer_lost_qualifiers():
    analyzer = QualifierAnalyzer()
    source = node("q1", "VarDecl", qualifiers=["const", "volatile"])
    target = node("q2", "VarDecl", qualifiers=["volatile"])
    assert analyzer.lost_qualifiers(source, target) == ["const"]


def _function_with_two_returns():
    fn = node("f1", "FunctionDecl", children=["body"])
    body = node("body", "CompoundStmt", parent="f1", children=["r1", "r2"])
    r1 = node("r1", "ReturnStmt", parent="body")
    r2 = node("r2", "ReturnStmt", parent="body")
    return AstGraph([fn, body, r1, r2]), fn


def test_cfg_builder_exit_points_and_unreachable():
    graph, fn = _function_with_two_returns()
    cfg = CFGBuilder()
    assert len(cfg.exit_points(fn, graph)) == 2
    assert not cfg.has_single_exit(fn, graph)


def test_cfg_builder_switch_fallthrough():
    switch_node = node("sw", "SwitchStmt", children=["body"])
    body = node("body", "CompoundStmt", parent="sw", children=["case1", "stmt1", "case2", "brk"])
    case1 = node("case1", "CaseStmt", parent="body")
    stmt1 = node("stmt1", "CallExpr", parent="body")
    case2 = node("case2", "CaseStmt", parent="body")
    brk = node("brk", "BreakStmt", parent="body")
    graph = AstGraph([switch_node, body, case1, stmt1, case2, brk])
    fallthrough = CFGBuilder().switch_blocks_without_terminator(switch_node, graph)
    assert len(fallthrough) == 1
    assert fallthrough[0]["node_id"] == "case1"


def test_dataflow_engine_uninitialized_read():
    fn = node("f1", "FunctionDecl", children=["decl", "use"])
    decl = node("decl", "VarDecl", parent="f1", semantic_properties={"name": "x"})
    use = node(
        "use",
        "DeclRefExpr",
        parent="f1",
        semantic_properties={"name": "x"},
        source_range={"line_start": 2, "column_start": 1},
    )
    graph = AstGraph([fn, decl, use])
    engine = DataFlowEngine()
    result = engine.uninitialized_read(decl, fn, graph)
    assert result is not None
    assert result["node_id"] == "use"


def test_symbol_index_duplicate_names_within_significant_chars():
    n1 = node("n1", "VarDecl", semantic_properties={"name": "very_long_identifier_one"})
    n2 = node("n2", "VarDecl", semantic_properties={"name": "very_long_identifier_two"})
    graph = AstGraph([n1, n2])
    index = SymbolIndex(graph)
    collisions = index.duplicate_names_within(20)
    assert ("very_long_identifier_one", "very_long_identifier_two") in collisions


def test_linkage_index_detects_incompatible_types_across_tus():
    tu1_fn = node(
        "a1",
        "FunctionDecl",
        semantic_properties={"name": "shared_fn", "storage_class": "external"},
        type_information={"spelling": "int (void)"},
    )
    tu2_fn = node(
        "b1",
        "FunctionDecl",
        semantic_properties={"name": "shared_fn", "storage_class": "external"},
        type_information={"spelling": "void (void)"},
    )
    graph1 = AstGraph([tu1_fn])
    graph2 = AstGraph([tu2_fn])
    data = LinkageIndex.build([("tu1", "a.c", graph1), ("tu2", "b.c", graph2)])
    index = LinkageIndex(data)
    assert index.incompatible_type_spellings("shared_fn")


def test_macro_analyzer_unparenthesized_body_and_reserved_identifier():
    analyzer = MacroAnalyzer()
    macro_table = {
        "macro_definitions": [
            {"name": "SQUARE", "value": "x * x", "is_function_like": True},
            {"name": "_RESERVED", "value": "1", "is_function_like": False},
        ]
    }
    macros = analyzer.macro_definitions(macro_table)
    assert analyzer.has_unparenthesized_operator_body(macros[0])
    assert analyzer.is_reserved_identifier("_RESERVED")
    assert not analyzer.is_reserved_identifier("normal_name")


def test_expression_classifier_constant_and_assignment_in_condition():
    classifier = ExpressionClassifier()
    lit1 = node("l1", "IntegerLiteral")
    lit2 = node("l2", "IntegerLiteral")
    binary = node("b1", "BinaryOperator", children=["l1", "l2"], semantic_properties={"opcode": "+"})
    graph = AstGraph([binary, lit1, lit2])
    lit1["parent_id"] = "b1"
    lit2["parent_id"] = "b1"
    assert classifier.is_constant_expression(binary, graph)

    if_stmt = node("if1", "IfStmt", children=["assign"])
    assign = node(
        "assign", "BinaryOperator", parent="if1", semantic_properties={"opcode": "="}
    )
    cond_graph = AstGraph([if_stmt, assign])
    assert classifier.is_assignment_used_as_condition(assign, cond_graph)
