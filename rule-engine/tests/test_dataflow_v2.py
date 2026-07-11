from misra_platform_rules.analyzers.cfg_engine import CFGEngine
from misra_platform_rules.analyzers.dataflow_engine_v2 import DataFlowEngineV2
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
            "semantic_properties": kwargs.pop("semantic_properties", {}),
        }
        payload.update(kwargs)
        self.nodes.append(payload)
        if parent:
            next(n for n in self.nodes if n["node_id"] == parent)["children_ids"].append(node_id)
        return node_id

    def graph(self) -> AstGraph:
        return AstGraph(self.nodes)

    def decl_ref(self, name: str, parent: str) -> str:
        return self.node("DeclRefExpr", parent=parent, semantic_properties={"name": name})

    def assign(self, name: str, parent: str, rhs_kind: str = "IntegerLiteral", rhs_props=None) -> str:
        op = self.node("BinaryOperator", parent=parent, semantic_properties={"opcode": "="})
        self.decl_ref(name, op)
        self.node(rhs_kind, parent=op, semantic_properties=rhs_props or {})
        return op

    def call(self, callee: str, parent: str, arg_names: list[str] | None = None) -> str:
        call_node = self.node("CallExpr", parent=parent, semantic_properties={"callee": callee})
        for arg_name in arg_names or []:
            self.decl_ref(arg_name, call_node)
        return call_node


def _build(b: _Builder, fn: str) -> tuple:
    graph = b.graph()
    function_node = graph.get(fn)
    cfg = CFGEngine().build(function_node, graph)
    return function_node, cfg, graph


def test_uninitialized_read_detected_on_declaring_block():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    b.decl_ref("x", body)  # read with nothing between decl and use
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().uninitialized_reads(function_node, cfg, graph)
    assert any(n.get("semantic_properties", {}).get("name") == "x" for n in findings)


def test_uninitialized_read_not_flagged_after_write():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    b.assign("x", body)
    b.decl_ref("x", body)
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().uninitialized_reads(function_node, cfg, graph)
    assert findings == []


def test_uninitialized_read_flagged_when_only_one_branch_initializes():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    if_stmt = b.node("IfStmt", parent=body)
    b.decl_ref("cond", if_stmt)
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.assign("x", then_branch)
    # no else branch: on the false path x is still uninitialized
    b.decl_ref("x", body)
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().uninitialized_reads(function_node, cfg, graph)
    assert any(n.get("semantic_properties", {}).get("name") == "x" for n in findings)


def test_dead_store_detects_overwritten_value_never_read():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    first_write = b.assign("x", body)
    b.assign("x", body)
    b.decl_ref("x", body)
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().dead_stores(cfg, graph)
    first_write_lhs = graph.children(first_write)[0]
    assert any(n["node_id"] == first_write_lhs["node_id"] for n in findings)


def test_dead_store_not_flagged_when_value_is_read():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    b.assign("x", body)
    b.decl_ref("x", body)
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().dead_stores(cfg, graph)
    assert findings == []


def test_liveness_propagates_across_branch_that_reads_variable():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "x"})
    write_op = b.assign("x", body)
    if_stmt = b.node("IfStmt", parent=body)
    b.decl_ref("cond", if_stmt)
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.decl_ref("x", then_branch)
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    write_block = cfg.block_containing(write_op)
    assert write_block is not None
    live_out = DataFlowEngineV2().liveness(cfg, graph)
    assert "x" in live_out[write_block.block_id]


def test_taint_propagates_from_source_to_sink_across_branch():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "buf"})
    b.node("VarDecl", parent=body, semantic_properties={"name": "n"})
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.decl_ref("n", op)
    b.call("recv", op)  # n = recv(...)

    if_stmt = b.node("IfStmt", parent=body)
    b.decl_ref("cond", if_stmt)
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.call("memcpy", then_branch, arg_names=["buf", "n"])

    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().propagate_taint(function_node, cfg, graph)
    assert any(f.tainted_argument == "n" and f.sink_function_name == "memcpy" for f in findings)


def test_taint_cleared_by_intervening_safe_assignment():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "n"})
    op = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    b.decl_ref("n", op)
    b.call("recv", op)  # n = recv(...)
    b.assign("n", body, rhs_kind="IntegerLiteral")  # n = 0 (sanitized)
    b.call("memcpy", body, arg_names=["buf", "n"])
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    findings = DataFlowEngineV2().propagate_taint(function_node, cfg, graph)
    assert findings == []


def test_null_check_facts_narrow_on_true_and_false_edges():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    if_stmt = b.node("IfStmt", parent=body)
    condition = b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "!="})
    b.decl_ref("p", condition)
    b.node("IntegerLiteral", parent=condition, semantic_properties={"value": "0"})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.call("use", then_branch, arg_names=["p"])
    b.node("ReturnStmt", parent=body)

    function_node, cfg, graph = _build(b, fn)
    facts = DataFlowEngineV2().null_check_facts(cfg, graph)
    states = {fact.state for fact in facts if fact.variable == "p"}
    assert states == {"null", "non_null"}


def test_variable_lifetime_range_and_escape_detection():
    b = _Builder()
    fn = b.node("FunctionDecl")
    body = b.node("CompoundStmt", parent=fn)
    b.node("VarDecl", parent=body, semantic_properties={"name": "local"})
    escaping_use = b.node("CallExpr", parent=body, semantic_properties={"callee": "store_pointer"})

    function_node, cfg, graph = _build(b, fn)
    ranges = DataFlowEngineV2().variable_lifetime_ranges(function_node, graph)
    assert len(ranges) == 1
    lifetime = ranges[0]
    assert lifetime.variable == "local"
    far_future_use = {"source_range": {"line_start": lifetime.last_line + 100}}
    assert DataFlowEngineV2().escapes_lifetime(lifetime, far_future_use)
    assert not DataFlowEngineV2().escapes_lifetime(lifetime, graph.get(escaping_use))
