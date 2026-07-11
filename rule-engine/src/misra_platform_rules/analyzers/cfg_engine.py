"""Phase 4: a real control-flow graph (basic blocks + edges), replacing the
Phase 3 `CFGBuilder` structural approximation for anything that needs sound
CFG-shaped facts (dataflow, taint, path-sensitive analysis, visualization).

`CFGBuilder` (Phase 3) is kept as-is for the rules already built on its
AST-shape heuristics; new/upgraded rules and the new dataflow engine should
use `CFGEngine.build()` instead.

Design:
  - A `BasicBlock` is a straight-line run of statements with a single entry
    and single exit (no internal branching).
  - `CFGEdge` connects blocks, tagged with a `kind` (`fallthrough`,
    `true`, `false`, `loop_back`, `break`, `continue`, `goto`, `case`,
    `default`, `switch_fallthrough`) so downstream consumers (dataflow,
    visualization) know *why* an edge exists.
  - `ENTRY` and `EXIT` are synthetic blocks every function has exactly one
    of; every real block is reachable from `ENTRY` in a sound CFG, and
    `unreachable_blocks()` reports the ones that aren't.
  - `goto`/`label` support is best-effort: forward/backward gotos within the
    same function body are wired once every label has been discovered (two
    passes), matching real C semantics (labels have function scope).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

ENTRY_ID = "__entry__"
EXIT_ID = "__exit__"

_LOOP_KINDS = {"ForStmt", "WhileStmt", "DoStmt"}


@dataclass(slots=True)
class CFGEdge:
    source: str
    target: str
    kind: str = "fallthrough"
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "kind": self.kind, "label": self.label}


@dataclass(slots=True)
class BasicBlock:
    block_id: str
    statements: list[dict[str, Any]] = field(default_factory=list)
    kind: str = "normal"  # normal | entry | exit | branch | loop_header | switch

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "kind": self.kind,
            "statement_node_ids": [stmt.get("node_id") for stmt in self.statements],
            "statement_kinds": [stmt.get("node_kind") for stmt in self.statements],
            "line_start": self.statements[0].get("source_range", {}).get("line_start")
            if self.statements
            else None,
            "line_end": self.statements[-1].get("source_range", {}).get("line_end")
            if self.statements
            else None,
        }


@dataclass(slots=True)
class ControlFlowGraph:
    function_node_id: str
    blocks: dict[str, BasicBlock] = field(default_factory=dict)
    edges: list[CFGEdge] = field(default_factory=list)

    def successors(self, block_id: str) -> list[CFGEdge]:
        return [edge for edge in self.edges if edge.source == block_id]

    def predecessors(self, block_id: str) -> list[CFGEdge]:
        return [edge for edge in self.edges if edge.target == block_id]

    def reachable_blocks(self) -> set[str]:
        visited: set[str] = set()
        stack = [ENTRY_ID]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for edge in self.successors(current):
                stack.append(edge.target)
        return visited

    def unreachable_blocks(self) -> list[BasicBlock]:
        """Blocks not reachable from `ENTRY`. Empty (statement-less) blocks
        are excluded: they're structural scaffolding introduced by the
        builder (e.g. the placeholder block allocated right after a
        `return`/`break`/`goto`), not actual unreachable *code*."""
        reachable = self.reachable_blocks()
        return [
            block
            for block_id, block in self.blocks.items()
            if block_id not in reachable and block_id not in (ENTRY_ID, EXIT_ID) and block.statements
        ]

    def exit_edges(self) -> list[CFGEdge]:
        return self.predecessors(EXIT_ID)

    def has_single_exit_path(self) -> bool:
        return len(self.exit_edges()) <= 1

    def block_containing(self, node_id: str) -> BasicBlock | None:
        for block in self.blocks.values():
            if any(stmt.get("node_id") == node_id for stmt in block.statements):
                return block
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "function_node_id": self.function_node_id,
            "entry_block_id": ENTRY_ID,
            "exit_block_id": EXIT_ID,
            "blocks": [block.to_dict() for block in self.blocks.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "unreachable_block_ids": [block.block_id for block in self.unreachable_blocks()],
        }

    def to_dot(self) -> str:
        lines = ["digraph CFG {", '  node [shape=box, fontname="monospace"];']
        unreachable_ids = {block.block_id for block in self.unreachable_blocks()}
        for block_id, block in self.blocks.items():
            label = block_id if block_id in (ENTRY_ID, EXIT_ID) else "\\n".join(
                f"{stmt.get('node_kind', '?')}" for stmt in block.statements
            ) or "(empty)"
            color = "red" if block_id in unreachable_ids else "black"
            lines.append(f'  "{block_id}" [label="{label}", color={color}];')
        for edge in self.edges:
            style = "dashed" if edge.kind in ("false", "break", "goto") else "solid"
            edge_label = edge.label or edge.kind
            lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{edge_label}", style={style}];')
        lines.append("}")
        return "\n".join(lines)


class _BlockFactory:
    def __init__(self) -> None:
        self._counter = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"b{self._counter}"


class CFGEngine:
    """Builds a real basic-block CFG for a single `FunctionDecl` node.

    Not thread-safe across concurrent `build()` calls on the *same* instance
    (each build resets `_sequence_tails`); construct a fresh `CFGEngine()` per
    thread/worker, or reuse one only for sequential builds — consistent with
    how the other Phase 3 analyzers are used (cheap to instantiate, cached
    per-thread via `BaseRulePlugin`).
    """

    def build(self, function_node: dict[str, Any], graph: "AstGraph") -> ControlFlowGraph:
        # Reset per-build state. Block ids restart at "b1" on every call, so
        # a stale cross-build `_sequence_tails` entry could otherwise be
        # looked up under a colliding key from a *different* function.
        self._sequence_tails: dict[str, str] = {}

        cfg = ControlFlowGraph(function_node_id=function_node["node_id"])
        cfg.blocks[ENTRY_ID] = BasicBlock(ENTRY_ID, kind="entry")
        cfg.blocks[EXIT_ID] = BasicBlock(EXIT_ID, kind="exit")

        factory = _BlockFactory()
        statements = self._body_statements(function_node, graph)

        label_targets: dict[str, str] = {}
        pending_gotos: list[tuple[str, str]] = []  # (goto_block_id, label_name)

        if not statements:
            cfg.edges.append(CFGEdge(ENTRY_ID, EXIT_ID, kind="fallthrough"))
            return cfg

        entry_of_body = self._build_block_sequence(
            statements=statements,
            graph=graph,
            cfg=cfg,
            factory=factory,
            exit_target=EXIT_ID,
            loop_stack=[],
            label_targets=label_targets,
            pending_gotos=pending_gotos,
        )
        cfg.edges.append(CFGEdge(ENTRY_ID, entry_of_body, kind="fallthrough"))

        top_tail = self._tail_of(entry_of_body)
        if not cfg.successors(top_tail) and cfg.predecessors(top_tail):
            # Implicit fall-off-the-end return (no explicit `return` as the
            # last statement, or an empty body) — only wire this when the
            # tail block is actually reachable; a tail block with zero
            # predecessors is just the builder's dangling scaffolding after
            # a statement that already transferred control away (e.g. the
            # placeholder allocated right after an explicit `return`).
            cfg.edges.append(CFGEdge(top_tail, EXIT_ID, kind="implicit_return"))

        for goto_block_id, label_name in pending_gotos:
            target = label_targets.get(label_name)
            if target:
                cfg.edges.append(CFGEdge(goto_block_id, target, kind="goto", label=label_name))
            else:
                # Label not found within this function body: leave the goto
                # dangling to EXIT rather than silently dropping the edge, so
                # unreachable-code analysis doesn't produce a false unreachable
                # verdict for code after it.
                cfg.edges.append(CFGEdge(goto_block_id, EXIT_ID, kind="goto", label=label_name))

        self._prune_empty_pass_through_blocks(cfg)
        return cfg

    _NON_STATEMENT_KINDS = {"ParmVarDecl", "BuiltinType", "PointerType", "RecordType", "EnumDecl"}

    def _body_statements(self, function_node: dict[str, Any], graph: "AstGraph") -> list[dict[str, Any]]:
        """The function's body statement list. Prefers an explicit
        `CompoundStmt` child (real clang-worker output always has exactly
        one, except for prototypes with no body at all). Falls back to
        treating the `FunctionDecl`'s own non-parameter/non-type children
        as a flat statement list, for simplified/hand-built ASTs (unit and
        conformance fixtures) that skip the `CompoundStmt` wrapper."""
        children = graph.children(function_node["node_id"])
        for child in children:
            if child.get("node_kind") == "CompoundStmt":
                return graph.children(child["node_id"])
        return [child for child in children if child.get("node_kind") not in self._NON_STATEMENT_KINDS]

    def _new_block(self, cfg: ControlFlowGraph, factory: _BlockFactory, kind: str = "normal") -> BasicBlock:
        block = BasicBlock(factory.next_id(), kind=kind)
        cfg.blocks[block.block_id] = block
        return block

    def _build_block_sequence(
        self,
        *,
        statements: list[dict[str, Any]],
        graph: "AstGraph",
        cfg: ControlFlowGraph,
        factory: _BlockFactory,
        exit_target: str,
        loop_stack: list[tuple[str, str]],  # (continue_target, break_target)
        label_targets: dict[str, str],
        pending_gotos: list[tuple[str, str]],
    ) -> str:
        """Build blocks for a flat statement list; returns the id of the
        first block (the entry point of this sequence)."""
        current = self._new_block(cfg, factory)
        first_block_id = current.block_id
        index = 0

        while index < len(statements):
            statement = statements[index]
            kind = statement.get("node_kind")

            if kind == "LabelStmt":
                label_name = statement.get("semantic_properties", {}).get("name", statement["node_id"])
                if current.statements:
                    next_block = self._new_block(cfg, factory)
                    cfg.edges.append(CFGEdge(current.block_id, next_block.block_id, kind="fallthrough"))
                    current = next_block
                label_targets[label_name] = current.block_id
                current.statements.append(statement)
                index += 1
                continue

            if kind == "IfStmt":
                current, index = self._handle_if(
                    statement, statements, index, graph, cfg, factory, current,
                    exit_target, loop_stack, label_targets, pending_gotos,
                )
                continue

            if kind in _LOOP_KINDS:
                current, index = self._handle_loop(
                    statement, index, graph, cfg, factory, current,
                    exit_target, loop_stack, label_targets, pending_gotos,
                )
                continue

            if kind == "SwitchStmt":
                current, index = self._handle_switch(
                    statement, index, graph, cfg, factory, current,
                    exit_target, loop_stack, label_targets, pending_gotos,
                )
                continue

            if kind == "CompoundStmt":
                nested_entry = self._build_block_sequence(
                    statements=graph.children(statement["node_id"]),
                    graph=graph, cfg=cfg, factory=factory, exit_target=exit_target,
                    loop_stack=loop_stack, label_targets=label_targets, pending_gotos=pending_gotos,
                )
                cfg.edges.append(CFGEdge(current.block_id, nested_entry, kind="fallthrough"))
                current = self._new_block(cfg, factory)
                index += 1
                continue

            if kind == "ReturnStmt":
                current.statements.append(statement)
                cfg.edges.append(CFGEdge(current.block_id, exit_target, kind="return"))
                current = self._new_block(cfg, factory)
                index += 1
                continue

            if kind == "BreakStmt":
                current.statements.append(statement)
                if loop_stack:
                    _, break_target = loop_stack[-1]
                    cfg.edges.append(CFGEdge(current.block_id, break_target, kind="break"))
                current = self._new_block(cfg, factory)
                index += 1
                continue

            if kind == "ContinueStmt":
                current.statements.append(statement)
                if loop_stack:
                    continue_target, _ = loop_stack[-1]
                    cfg.edges.append(CFGEdge(current.block_id, continue_target, kind="continue"))
                current = self._new_block(cfg, factory)
                index += 1
                continue

            if kind == "GotoStmt":
                current.statements.append(statement)
                label_name = statement.get("semantic_properties", {}).get("target_label", "")
                pending_gotos.append((current.block_id, label_name))
                current = self._new_block(cfg, factory)
                index += 1
                continue

            current.statements.append(statement)
            index += 1

        # Wire final block of this sequence onward. The caller links our
        # returned first_block_id in; here we just leave `current` dangling
        # for the caller/parent to connect (it becomes the "fallthrough tail").
        # `_sequence_tails` is reset at the top of every `build()` call (see
        # above) so entry-id collisions across separate builds are safe.
        self._sequence_tails.setdefault(first_block_id, current.block_id)
        return first_block_id

    def _tail_of(self, entry_block_id: str) -> str:
        return self._sequence_tails.get(entry_block_id, entry_block_id)

    def _handle_if(
        self, statement, statements, index, graph, cfg, factory, current,
        exit_target, loop_stack, label_targets, pending_gotos,
    ) -> tuple[BasicBlock, int]:
        current.statements.append(statement)
        branch_block_id = current.block_id
        children = graph.children(statement["node_id"])
        # Convention (see synthetic builders / clang AST): child[0] = condition,
        # child[1] = then-branch, optional child[2] = else-branch.
        then_branch = children[1] if len(children) > 1 else None
        else_branch = children[2] if len(children) > 2 else None

        join_block = self._new_block(cfg, factory)

        if then_branch is not None:
            then_entry = self._as_sequence_entry(
                then_branch, graph, cfg, factory, exit_target, loop_stack, label_targets, pending_gotos
            )
            cfg.edges.append(CFGEdge(branch_block_id, then_entry, kind="true"))
            then_tail = self._tail_of(then_entry)
            cfg.edges.append(CFGEdge(then_tail, join_block.block_id, kind="fallthrough"))
        else:
            cfg.edges.append(CFGEdge(branch_block_id, join_block.block_id, kind="true"))

        if else_branch is not None:
            else_entry = self._as_sequence_entry(
                else_branch, graph, cfg, factory, exit_target, loop_stack, label_targets, pending_gotos
            )
            cfg.edges.append(CFGEdge(branch_block_id, else_entry, kind="false"))
            else_tail = self._tail_of(else_entry)
            cfg.edges.append(CFGEdge(else_tail, join_block.block_id, kind="fallthrough"))
        else:
            cfg.edges.append(CFGEdge(branch_block_id, join_block.block_id, kind="false"))

        return join_block, index + 1

    def _as_sequence_entry(
        self, node, graph, cfg, factory, exit_target, loop_stack, label_targets, pending_gotos
    ) -> str:
        if node.get("node_kind") == "CompoundStmt":
            return self._build_block_sequence(
                statements=graph.children(node["node_id"]), graph=graph, cfg=cfg, factory=factory,
                exit_target=exit_target, loop_stack=loop_stack, label_targets=label_targets,
                pending_gotos=pending_gotos,
            )
        return self._build_block_sequence(
            statements=[node], graph=graph, cfg=cfg, factory=factory, exit_target=exit_target,
            loop_stack=loop_stack, label_targets=label_targets, pending_gotos=pending_gotos,
        )

    def _handle_loop(
        self, statement, index, graph, cfg, factory, current,
        exit_target, loop_stack, label_targets, pending_gotos,
    ) -> tuple[BasicBlock, int]:
        kind = statement.get("node_kind")
        header = self._new_block(cfg, factory, kind="loop_header")
        header.statements.append(statement)
        after_loop = self._new_block(cfg, factory)

        cfg.edges.append(CFGEdge(current.block_id, header.block_id, kind="fallthrough"))

        children = graph.children(statement["node_id"])
        if kind == "DoStmt":
            body_node = children[0] if children else None
        else:
            body_node = children[-1] if children else None

        new_loop_stack = [*loop_stack, (header.block_id, after_loop.block_id)]

        if kind == "DoStmt":
            # do { body } while(cond): body always runs once, then loops back
            # to the header for the condition check.
            if body_node is not None:
                body_entry = self._as_sequence_entry(
                    body_node, graph, cfg, factory, exit_target, new_loop_stack, label_targets, pending_gotos
                )
                cfg.edges.append(CFGEdge(header.block_id, body_entry, kind="fallthrough"))
                body_tail = self._tail_of(body_entry)
                cfg.edges.append(CFGEdge(body_tail, header.block_id, kind="loop_back"))
            cfg.edges.append(CFGEdge(header.block_id, after_loop.block_id, kind="false"))
        else:
            if body_node is not None:
                body_entry = self._as_sequence_entry(
                    body_node, graph, cfg, factory, exit_target, new_loop_stack, label_targets, pending_gotos
                )
                cfg.edges.append(CFGEdge(header.block_id, body_entry, kind="true"))
                body_tail = self._tail_of(body_entry)
                cfg.edges.append(CFGEdge(body_tail, header.block_id, kind="loop_back"))
            cfg.edges.append(CFGEdge(header.block_id, after_loop.block_id, kind="false"))

        return after_loop, index + 1

    def _handle_switch(
        self, statement, index, graph, cfg, factory, current,
        exit_target, loop_stack, label_targets, pending_gotos,
    ) -> tuple[BasicBlock, int]:
        current.statements.append(statement)
        switch_block_id = current.block_id
        after_switch = self._new_block(cfg, factory)
        new_loop_stack = [*loop_stack, (switch_block_id, after_switch.block_id)]

        body_candidates = [
            child for child in graph.children(statement["node_id"]) if child.get("node_kind") == "CompoundStmt"
        ]
        if not body_candidates:
            cfg.edges.append(CFGEdge(switch_block_id, after_switch.block_id, kind="fallthrough"))
            return after_switch, index + 1

        case_statements = graph.children(body_candidates[0]["node_id"])
        case_group_starts: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        current_group: list[dict[str, Any]] = []
        current_case_stmt: dict[str, Any] | None = None

        for stmt in case_statements:
            if stmt.get("node_kind") in ("CaseStmt", "DefaultStmt"):
                if current_case_stmt is not None:
                    case_group_starts.append((current_case_stmt, current_group))
                current_case_stmt = stmt
                current_group = []
            else:
                current_group.append(stmt)
        if current_case_stmt is not None:
            case_group_starts.append((current_case_stmt, current_group))

        previous_tail: str | None = None
        for case_stmt, group_statements in case_group_starts:
            label = "default" if case_stmt.get("node_kind") == "DefaultStmt" else "case"
            group_entry = self._build_block_sequence(
                statements=[case_stmt, *group_statements], graph=graph, cfg=cfg, factory=factory,
                exit_target=exit_target, loop_stack=new_loop_stack, label_targets=label_targets,
                pending_gotos=pending_gotos,
            )
            cfg.edges.append(CFGEdge(switch_block_id, group_entry, kind=label))
            if previous_tail is not None:
                # Fallthrough from the previous case group into this one,
                # unless the previous group already terminated (break/return).
                if not self._terminates(cfg, previous_tail):
                    cfg.edges.append(CFGEdge(previous_tail, group_entry, kind="switch_fallthrough"))
            previous_tail = self._tail_of(group_entry)

        if previous_tail is not None and not self._terminates(cfg, previous_tail):
            cfg.edges.append(CFGEdge(previous_tail, after_switch.block_id, kind="fallthrough"))
        if not any(case_stmt.get("node_kind") == "DefaultStmt" for case_stmt, _ in case_group_starts):
            cfg.edges.append(CFGEdge(switch_block_id, after_switch.block_id, kind="no_match"))

        return after_switch, index + 1

    def _terminates(self, cfg: ControlFlowGraph, block_id: str) -> bool:
        return any(edge.kind in ("return", "break", "goto") for edge in cfg.successors(block_id))

    def _prune_empty_pass_through_blocks(self, cfg: ControlFlowGraph) -> None:
        """Collapse blocks that have no statements and exactly one outgoing
        fallthrough edge and no incoming branch-kind edges that need a
        distinct target for labeling; keeps the graph readable without
        changing reachability semantics."""
        changed = True
        while changed:
            changed = False
            for block_id in list(cfg.blocks.keys()):
                if block_id in (ENTRY_ID, EXIT_ID):
                    continue
                block = cfg.blocks.get(block_id)
                if block is None or block.statements:
                    continue
                outgoing = cfg.successors(block_id)
                if len(outgoing) != 1 or outgoing[0].kind != "fallthrough":
                    continue
                target = outgoing[0].target
                if target == block_id:
                    continue
                incoming = cfg.predecessors(block_id)
                for edge in incoming:
                    edge.target = target
                cfg.edges = [edge for edge in cfg.edges if edge is not outgoing[0]]
                del cfg.blocks[block_id]
                changed = True
