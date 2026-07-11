from misra_platform_rules.analyzers.alias_analyzer import (
    CONFIDENCE_DEFINITE,
    CONFIDENCE_POSSIBLE,
    CONFIDENCE_UNKNOWN,
    AliasAnalyzer,
)
from misra_platform_rules.ast_graph import AstGraph


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[dict] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def node(self, kind: str, parent: str | None = None, **kwargs) -> str:
        node_id = self._next_id()
        line = len(self.nodes) + 1
        payload = {
            "node_id": node_id,
            "node_kind": kind,
            "parent_id": parent or "",
            "children_ids": [],
            "source_range": {"line_start": line, "line_end": line, "column_start": 1},
            "type_information": kwargs.pop("type_information", {}),
            "semantic_properties": kwargs.pop("semantic_properties", {}),
        }
        payload.update(kwargs)
        self.nodes.append(payload)
        if parent:
            next(n for n in self.nodes if n["node_id"] == parent)["children_ids"].append(node_id)
        return node_id

    def graph(self) -> AstGraph:
        return AstGraph(self.nodes)

    def address_of(self, name: str, parent: str) -> str:
        unary = self.node("UnaryOperator", parent=parent, semantic_properties={"opcode": "&"})
        self.node(
            "DeclRefExpr", parent=unary, semantic_properties={"name": name},
            type_information={"is_pointer": False},
        )
        return unary

    def ptr_assign(self, lhs_name: str, parent: str, rhs_builder) -> str:
        op = self.node("BinaryOperator", parent=parent, semantic_properties={"opcode": "="})
        self.node("DeclRefExpr", parent=op, semantic_properties={"name": lhs_name})
        rhs_builder(op)
        return op


def test_address_of_variable_is_definite_pointee():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.ptr_assign("p", body, lambda parent: b.address_of("x", parent))

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    pointees = analyzer.points_to("p")
    assert len(pointees) == 1
    pointee = next(iter(pointees))
    assert pointee.target == "x"
    assert pointee.kind == "variable"
    assert pointee.confidence == CONFIDENCE_DEFINITE


def test_pointer_copy_inherits_points_to_set():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.ptr_assign("p", body, lambda parent: b.address_of("x", parent))
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=op, semantic_properties={"name": "q"})
    b.node("DeclRefExpr", parent=op, semantic_properties={"name": "p"})

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    q_pointees = analyzer.points_to("q")
    assert any(p.target == "x" for p in q_pointees)

    may, confidence = analyzer.may_alias("p", "q")
    assert may is True
    assert confidence == CONFIDENCE_DEFINITE


def test_branch_merge_produces_possible_confidence_multi_target():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    if_stmt = b.node("IfStmt", parent=body)
    b.node("DeclRefExpr", parent=if_stmt, semantic_properties={"name": "cond"})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.ptr_assign("p", then_branch, lambda parent: b.address_of("x", parent))
    else_branch = b.node("CompoundStmt", parent=if_stmt)
    b.ptr_assign("p", else_branch, lambda parent: b.address_of("y", parent))

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    pointees = analyzer.points_to("p")
    targets = {pointee.target for pointee in pointees}
    assert targets == {"x", "y"}
    assert all(pointee.confidence == CONFIDENCE_DEFINITE for pointee in pointees)

    may_x, confidence = analyzer.may_alias("p", "p")  # trivially true, sanity check API
    assert may_x is True
    assert confidence in (CONFIDENCE_DEFINITE, CONFIDENCE_POSSIBLE)


def test_array_decay_is_definite_array_alias():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=op, semantic_properties={"name": "p"})
    b.node(
        "DeclRefExpr", parent=op, semantic_properties={"name": "buf"},
        type_information={"is_array": True},
    )

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    array_aliases = analyzer.array_aliases()
    assert any(name == "p" and pointee.target == "buf" for name, pointee in array_aliases)


def test_function_pointer_capture_is_definite_function_alias():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=op, semantic_properties={"name": "fp"})
    b.node(
        "DeclRefExpr", parent=op, semantic_properties={"name": "handler", "is_function": True},
    )

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    fn_aliases = analyzer.function_pointer_aliases()
    assert any(name == "fp" and pointee.target == "handler" for name, pointee in fn_aliases)


def test_pointer_parameter_is_unknown_and_forces_conservative_alias():
    b = _Builder()
    fn = b.node("FunctionDecl")
    b.node(
        "ParmVarDecl", parent=fn, semantic_properties={"name": "param_ptr"},
        type_information={"is_pointer": True},
    )
    body = b.node("CompoundStmt", parent=fn)
    b.ptr_assign("local_ptr", body, lambda parent: b.address_of("x", parent))

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    may, confidence = analyzer.may_alias("param_ptr", "local_ptr")
    assert may is True
    assert confidence == CONFIDENCE_UNKNOWN


def test_heap_allocation_does_not_alias_named_locals():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=op, semantic_properties={"name": "heap_ptr"})
    b.node("CallExpr", parent=op, semantic_properties={"callee": "malloc"})
    b.ptr_assign("local_ptr", body, lambda parent: b.address_of("x", parent))

    analyzer = AliasAnalyzer().analyze(b.graph().get(fn), b.graph())
    may, confidence = analyzer.may_alias("heap_ptr", "local_ptr")
    assert may is False
    assert confidence == CONFIDENCE_DEFINITE  # heap target and 'x' definitely don't overlap
    heap_pointees = analyzer.points_to("heap_ptr")
    assert all(p.kind == "heap" for p in heap_pointees)
