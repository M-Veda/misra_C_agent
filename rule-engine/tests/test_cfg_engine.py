from misra_platform_rules.analyzers.cfg_engine import EXIT_ID, CFGEngine
from misra_platform_rules.ast_graph import AstGraph


class _Builder:
    """Local, minimal AST builder mirroring the conformance one, kept local
    so this test file has no cross-directory import dependency."""

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


def _function_with_body(builder: _Builder, statement_kinds_and_children) -> tuple[str, str]:
    """Builds `FunctionDecl -> CompoundStmt -> [...]`. Returns (function_id, body_id)."""
    fn = builder.node("FunctionDecl")
    body = builder.node("CompoundStmt", parent=fn)
    return fn, body


def test_sequential_statements_have_single_exit_and_no_unreachable():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    b.node("VarDecl", parent=body)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    assert cfg.has_single_exit_path()
    assert cfg.unreachable_blocks() == []
    assert EXIT_ID in cfg.blocks


def test_statement_after_return_is_unreachable():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    b.node("ReturnStmt", parent=body)
    b.node("VarDecl", parent=body)  # dead code

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    unreachable_kinds = [stmt.get("node_kind") for block in cfg.unreachable_blocks() for stmt in block.statements]
    assert "VarDecl" in unreachable_kinds


def test_if_else_both_branches_return_makes_join_unreachable():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    if_stmt = b.node("IfStmt", parent=body)
    b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "=="})  # condition
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.node("ReturnStmt", parent=then_branch)
    else_branch = b.node("CompoundStmt", parent=if_stmt)
    b.node("ReturnStmt", parent=else_branch)
    b.node("VarDecl", parent=body)  # unreachable: both branches always return

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    unreachable_kinds = [stmt.get("node_kind") for block in cfg.unreachable_blocks() for stmt in block.statements]
    assert "VarDecl" in unreachable_kinds
    # Two return statements => two distinct `return`-kind edges into EXIT
    # (there may additionally be a phantom `implicit_return` edge from the
    # dead join block after both branches return — that edge is inert since
    # the join block itself is unreachable).
    return_edges = [edge for edge in cfg.exit_edges() if edge.kind == "return"]
    assert len(return_edges) == 2


def test_if_without_else_has_true_and_false_edges_from_branch_block():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    if_stmt = b.node("IfStmt", parent=body)
    b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "!="})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    b.node("CallExpr", parent=then_branch)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    branch_block = cfg.block_containing(if_stmt)
    assert branch_block is not None
    kinds = {edge.kind for edge in cfg.successors(branch_block.block_id)}
    assert "true" in kinds
    assert "false" in kinds
    assert cfg.unreachable_blocks() == []


def test_while_loop_has_loop_back_edge_and_break_reaches_after_loop():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    while_stmt = b.node("WhileStmt", parent=body)
    b.node("BinaryOperator", parent=while_stmt, semantic_properties={"opcode": "<"})
    loop_body = b.node("CompoundStmt", parent=while_stmt)
    inner_if = b.node("IfStmt", parent=loop_body)
    b.node("BinaryOperator", parent=inner_if, semantic_properties={"opcode": "=="})
    inner_then = b.node("CompoundStmt", parent=inner_if)
    b.node("BreakStmt", parent=inner_then)
    b.node("CallExpr", parent=loop_body)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    edge_kinds = {edge.kind for edge in cfg.edges}
    assert "loop_back" in edge_kinds
    assert "break" in edge_kinds
    assert cfg.unreachable_blocks() == []


def test_do_while_body_runs_before_condition_check():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    do_stmt = b.node("DoStmt", parent=body)
    do_body = b.node("CompoundStmt", parent=do_stmt)
    b.node("CallExpr", parent=do_body)
    b.node("BinaryOperator", parent=do_stmt, semantic_properties={"opcode": "<"})
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    # Header must have an outgoing fallthrough into the body (executes at least once).
    header_blocks = [block for block in cfg.blocks.values() if block.kind == "loop_header"]
    assert len(header_blocks) == 1
    header = header_blocks[0]
    into_body_kinds = {edge.kind for edge in cfg.successors(header.block_id)}
    assert "fallthrough" in into_body_kinds or "true" in into_body_kinds


def test_switch_fallthrough_without_break_and_break_terminates():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    switch_stmt = b.node("SwitchStmt", parent=body)
    b.node("DeclRefExpr", parent=switch_stmt)
    switch_body = b.node("CompoundStmt", parent=switch_stmt)
    case1 = b.node("CaseStmt", parent=switch_body)
    b.node("CallExpr", parent=switch_body)  # falls through, no break
    case2 = b.node("CaseStmt", parent=switch_body)
    b.node("BreakStmt", parent=switch_body)
    default_stmt = b.node("DefaultStmt", parent=switch_body)
    b.node("BreakStmt", parent=switch_body)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    edge_kinds = {edge.kind for edge in cfg.edges}
    assert "switch_fallthrough" in edge_kinds
    assert "case" in edge_kinds
    assert "default" in edge_kinds
    assert cfg.unreachable_blocks() == []
    _ = (case1, case2, default_stmt)


def test_goto_label_makes_forward_target_reachable():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    goto_stmt = b.node("GotoStmt", parent=body, semantic_properties={"target_label": "skip"})
    b.node("VarDecl", parent=body)  # skipped over, but still directly-following in AST order
    label_stmt = b.node("LabelStmt", parent=body, semantic_properties={"name": "skip"})
    b.node("ReturnStmt", parent=body)
    _ = (goto_stmt, label_stmt)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    edge_kinds = {edge.kind for edge in cfg.edges}
    assert "goto" in edge_kinds
    # The label's block must be reachable (via the goto edge), even though it
    # is also reachable structurally in this particular example.
    reachable = cfg.reachable_blocks()
    label_block = cfg.block_containing(label_stmt)
    assert label_block is not None
    assert label_block.block_id in reachable


def test_switch_not_at_index_zero_does_not_hang_and_terminates():
    """Regression test: `_handle_switch`/`_handle_loop` must advance the
    statement index by `index + 1`, not reset it to a literal `1`. A control
    statement that isn't the first statement in its block previously caused
    infinite reprocessing (and unbounded block/edge creation)."""
    b = _Builder()
    fn, body = _function_with_body(b, [])
    b.node("VarDecl", parent=body)
    b.node("CallExpr", parent=body)
    switch_stmt = b.node("SwitchStmt", parent=body)
    b.node("DeclRefExpr", parent=switch_stmt)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    assert len(cfg.blocks) < 20  # sane upper bound; a hang would blow this up


def test_loop_not_at_index_zero_does_not_hang_and_terminates():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    b.node("VarDecl", parent=body)
    b.node("CallExpr", parent=body)
    while_stmt = b.node("WhileStmt", parent=body)
    b.node("BinaryOperator", parent=while_stmt, semantic_properties={"opcode": "<"})
    loop_body = b.node("CompoundStmt", parent=while_stmt)
    b.node("CallExpr", parent=loop_body)
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    assert len(cfg.blocks) < 20


def test_to_dict_and_to_dot_are_well_formed():
    b = _Builder()
    fn, body = _function_with_body(b, [])
    b.node("ReturnStmt", parent=body)

    cfg = CFGEngine().build(b.graph().get(fn), b.graph())
    payload = cfg.to_dict()
    assert payload["function_node_id"] == fn
    assert "blocks" in payload and "edges" in payload
    dot = cfg.to_dot()
    assert dot.startswith("digraph CFG {")
    assert dot.strip().endswith("}")
