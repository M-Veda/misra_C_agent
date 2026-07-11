"""Phase 4: real CFG-based data flow (replaces the Phase 3 `DataFlowEngine`
textual-order approximation for anything that needs sound flow facts).

Implements the classical iterative worklist algorithms over
`cfg_engine.ControlFlowGraph`:

  - **Reaching definitions** (forward, may-analysis): which assignments to a
    variable can reach a given program point without being overwritten.
    Used for initialization-state ("is there an UNINIT pseudo-definition
    that reaches this read?") and for `dead_store` when combined with a
    reverse (liveness) query.
  - **Liveness** (backward, may-analysis): which variables' *current* value
    may still be read on some path forward from this point. A definition
    whose variable is not live immediately after it is a dead store.
  - **Taint propagation** (forward, may-analysis): marks values derived from
    a configurable set of "source" calls/parameters as tainted, and reports
    where a tainted value reaches a configurable set of "sink" calls.
  - **Path-sensitive null-check facts**: per-CFG-edge narrowing for the
    common `if (ptr == NULL)` / `if (ptr != NULL)` / `if (ptr)` / `if (!ptr)`
    patterns — a real (if narrow) instance of path sensitivity, since the
    same variable gets different facts on the `true` vs `false` edge out of
    the same branch block, rather than one flow-insensitive fact for the
    whole function.
  - **Variable lifetime ranges**: the AST-scope (not just CFG-block) range
    over which an automatic variable's storage is valid, used to catch
    pointers/aliases escaping their pointee's lifetime.

All analyses are intentionally *intra-procedural* and *flow-insensitive
across calls* (no interprocedural summaries) — see Phase 4 docs for the
soundness/precision trade-offs this implies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from misra_platform_rules.analyzers.cfg_engine import BasicBlock, ControlFlowGraph

if TYPE_CHECKING:
    from misra_platform_rules.analyzers.alias_analyzer import AliasAnalyzer
    from misra_platform_rules.ast_graph import AstGraph

UNINIT = "<uninit>"

_DEFAULT_TAINT_SOURCES = frozenset(
    {"recv", "read", "scanf", "sscanf", "getenv", "HAL_UART_Receive", "gets"}
)
_DEFAULT_TAINT_SINKS = frozenset(
    {"memcpy", "memmove", "strcpy", "strcat", "malloc", "system", "HAL_UART_Transmit"}
)


@dataclass(slots=True, frozen=True)
class Definition:
    variable: str
    site_node_id: str
    block_id: str

    def __hash__(self) -> int:  # frozen dataclass already hashable, explicit for clarity
        return hash((self.variable, self.site_node_id, self.block_id))


@dataclass(slots=True)
class TaintFinding:
    sink_call_node_id: str
    sink_function_name: str
    tainted_argument: str
    source_description: str


@dataclass(slots=True)
class NullCheckFact:
    block_id: str
    variable: str
    state: str  # "null" | "non_null"


@dataclass(slots=True)
class LifetimeRange:
    variable: str
    decl_node_id: str
    scope_node_id: str
    first_line: int
    last_line: int


class DataFlowEngineV2:
    def __init__(self, alias_analyzer: "AliasAnalyzer | None" = None) -> None:
        self._alias_analyzer = alias_analyzer

    # ------------------------------------------------------------------
    # def/use extraction
    # ------------------------------------------------------------------

    def _decl_ref_name(self, node: dict[str, Any]) -> str:
        return node.get("semantic_properties", {}).get("name", "")

    def _is_write_target(self, decl_ref: dict[str, Any], graph: "AstGraph") -> tuple[bool, bool]:
        """Returns (is_write, is_read_too) — compound assignment / ++/-- both
        read and write the same variable."""
        parent = graph.get(decl_ref.get("parent_id", ""))
        if not parent:
            return False, False
        if parent.get("node_kind") == "BinaryOperator":
            opcode = parent.get("semantic_properties", {}).get("opcode", "")
            children = graph.children(parent["node_id"])
            is_lhs = bool(children) and children[0].get("node_id") == decl_ref.get("node_id")
            if opcode == "=" and is_lhs:
                return True, False
            if opcode.endswith("=") and opcode not in ("==", "!=", "<=", ">=") and is_lhs:
                return True, True
        if parent.get("node_kind") == "UnaryOperator":
            opcode = parent.get("semantic_properties", {}).get("opcode", "")
            if opcode in ("++", "--"):
                return True, True
        return False, False

    def _statement_own_descendants(
        self, statement: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        """Descendants of `statement` that belong to *this* basic block,
        excluding any nested branch/loop/switch body — those are already
        separate blocks in the CFG (see `cfg_engine`), so including them
        here would double-count/misattribute their reads and writes to the
        wrong block. For a plain statement (assignment, call, return, ...)
        this is just its full subtree."""
        kind = statement.get("node_kind")
        children = graph.children(statement["node_id"])
        if kind == "IfStmt":
            own_children = children[:1]  # condition only; then/else are separate blocks
        elif kind in ("WhileStmt", "ForStmt", "SwitchStmt"):
            own_children = children[:-1] if children else []  # body is always last
        elif kind == "DoStmt":
            own_children = children[1:]  # body is first
        else:
            return [statement, *graph.descendants(statement["node_id"])]

        collected = [statement]
        for child in own_children:
            collected.append(child)
            collected.extend(graph.descendants(child["node_id"]))
        return collected

    def _linearize(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(node: dict[str, Any]) -> tuple[int, int]:
            source_range = node.get("source_range", {})
            return (source_range.get("line_start", 0), source_range.get("column_start", 0))

        return sorted(nodes, key=sort_key)

    def _block_events(
        self, block: BasicBlock, graph: "AstGraph"
    ) -> list[tuple[str, bool, bool, dict[str, Any]]]:
        """Ordered (variable_name, is_write, is_read_too, node) for every
        `DeclRefExpr` in this block, in source order. `is_read_too` is set
        for compound assignment / `++`/`--`, which both read and write."""
        refs: list[dict[str, Any]] = []
        for statement in block.statements:
            refs.extend(
                node
                for node in self._statement_own_descendants(statement, graph)
                if node.get("node_kind") == "DeclRefExpr"
            )
        refs = self._linearize(refs)

        events: list[tuple[str, bool, bool, dict[str, Any]]] = []
        for ref in refs:
            name = self._decl_ref_name(ref)
            if not name:
                continue
            is_write, is_read_too = self._is_write_target(ref, graph)
            events.append((name, is_write, is_read_too, ref))
        return events

    def block_def_use(
        self, block: BasicBlock, graph: "AstGraph"
    ) -> tuple[list[tuple[str, dict[str, Any]]], set[str]]:
        """Returns (ordered writes as (name, node) within the block, and the
        set of upward-exposed reads — variables read before any local write
        in this block)."""
        writes: list[tuple[str, dict[str, Any]]] = []
        exposed_reads: set[str] = set()
        locally_defined: set[str] = set()

        for name, is_write, is_read_too, ref in self._block_events(block, graph):
            if (not is_write) or is_read_too:
                if name not in locally_defined:
                    exposed_reads.add(name)
            if is_write:
                writes.append((name, ref))
                locally_defined.add(name)

        return writes, exposed_reads

    # ------------------------------------------------------------------
    # Reaching definitions (forward)
    # ------------------------------------------------------------------

    def reaching_definitions(
        self,
        function_node: dict[str, Any],
        cfg: ControlFlowGraph,
        graph: "AstGraph",
    ) -> dict[str, set[Definition]]:
        """Returns OUT[block_id] -> set of `Definition`s that may reach the
        end of that block, via the standard iterative worklist:
        OUT[B] = GEN[B] U (IN[B] - KILL[B]); IN[B] = union(OUT[P] for P in preds(B))
        """
        block_ids = list(cfg.blocks.keys())
        gen: dict[str, set[Definition]] = {}
        kill_vars: dict[str, set[str]] = {}

        for var_decl in self._uninitialized_local_decls(function_node, graph):
            name = self._decl_ref_name(var_decl)
            decl_block = cfg.block_containing(var_decl["node_id"])
            if decl_block is None or not name:
                continue
            gen.setdefault(decl_block.block_id, set()).add(
                Definition(name, UNINIT, decl_block.block_id)
            )

        for block_id in block_ids:
            block = cfg.blocks[block_id]
            writes, _ = self.block_def_use(block, graph)
            block_gen = gen.setdefault(block_id, set())
            block_kill = kill_vars.setdefault(block_id, set())
            for name, ref in writes:
                block_kill.add(name)
                block_gen = {d for d in block_gen if d.variable != name}
                block_gen.add(Definition(name, ref["node_id"], block_id))
            gen[block_id] = block_gen

        out_sets: dict[str, set[Definition]] = {block_id: set() for block_id in block_ids}
        changed = True
        while changed:
            changed = False
            for block_id in block_ids:
                incoming: set[Definition] = set()
                for edge in cfg.predecessors(block_id):
                    incoming |= out_sets.get(edge.source, set())
                killed_vars = kill_vars.get(block_id, set())
                survivors = {d for d in incoming if d.variable not in killed_vars}
                new_out = gen.get(block_id, set()) | survivors
                if new_out != out_sets[block_id]:
                    out_sets[block_id] = new_out
                    changed = True
        return out_sets

    def _uninitialized_local_decls(
        self, function_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        decls = []
        for node in graph.descendants(function_node["node_id"]):
            if node.get("node_kind") != "VarDecl":
                continue
            children = graph.children(node["node_id"])
            has_initializer = any(
                child.get("node_kind") not in ("BuiltinType", "RecordType", "PointerType")
                for child in children
            )
            if not has_initializer:
                decls.append(node)
        return decls

    def in_set(
        self, block_id: str, cfg: ControlFlowGraph, out_sets: dict[str, set[Definition]]
    ) -> set[Definition]:
        incoming: set[Definition] = set()
        for edge in cfg.predecessors(block_id):
            incoming |= out_sets.get(edge.source, set())
        return incoming

    def uninitialized_reads(
        self,
        function_node: dict[str, Any],
        cfg: ControlFlowGraph,
        graph: "AstGraph",
    ) -> list[dict[str, Any]]:
        """Every read that may observe the `UNINIT` pseudo-definition on some
        incoming path — sound (may-analysis) version of Phase 3's
        `DataFlowEngine.uninitialized_read` (which only checked the very
        first textual reference). Unlike a pure cross-block reaching-defs
        query, this also accounts for the *local* declaration-to-first-use
        gap within the same block (the `UNINIT` fact is generated at the
        declaration site itself, not received from a predecessor)."""
        out_sets = self.reaching_definitions(function_node, cfg, graph)
        findings: list[dict[str, Any]] = []

        decl_names_by_block: dict[str, set[str]] = {}
        for var_decl in self._uninitialized_local_decls(function_node, graph):
            decl_block = cfg.block_containing(var_decl["node_id"])
            name = self._decl_ref_name(var_decl)
            if decl_block is not None and name:
                decl_names_by_block.setdefault(decl_block.block_id, set()).add(name)

        for block_id, block in cfg.blocks.items():
            reaching_uninit: set[str] = {
                d.variable for d in self.in_set(block_id, cfg, out_sets) if d.site_node_id == UNINIT
            }
            reaching_uninit |= decl_names_by_block.get(block_id, set())

            for name, is_write, is_read_too, ref in self._block_events(block, graph):
                if name not in reaching_uninit:
                    continue
                if (not is_write) or is_read_too:
                    findings.append(ref)
                if is_write:
                    reaching_uninit.discard(name)
        return findings

    # ------------------------------------------------------------------
    # Liveness (backward)
    # ------------------------------------------------------------------

    def liveness(
        self, cfg: ControlFlowGraph, graph: "AstGraph"
    ) -> dict[str, set[str]]:
        """Returns LIVE_IN[block_id] -> set of variable names possibly read
        on some path starting at the top of that block."""
        block_ids = list(cfg.blocks.keys())
        use: dict[str, set[str]] = {}
        defs: dict[str, set[str]] = {}
        for block_id in block_ids:
            block = cfg.blocks[block_id]
            writes, exposed_reads = self.block_def_use(block, graph)
            use[block_id] = exposed_reads
            defs[block_id] = {name for name, _ in writes}

        live_in: dict[str, set[str]] = {block_id: set() for block_id in block_ids}
        live_out: dict[str, set[str]] = {block_id: set() for block_id in block_ids}
        changed = True
        while changed:
            changed = False
            for block_id in block_ids:
                out_set: set[str] = set()
                for edge in cfg.successors(block_id):
                    out_set |= live_in.get(edge.target, set())
                new_in = use[block_id] | (out_set - defs[block_id])
                if new_in != live_in[block_id] or out_set != live_out[block_id]:
                    live_in[block_id] = new_in
                    live_out[block_id] = out_set
                    changed = True
        return live_out

    def dead_stores(self, cfg: ControlFlowGraph, graph: "AstGraph") -> list[dict[str, Any]]:
        """A *pure* (non-compound) write whose variable is not live
        immediately after it — no read on any path before either the next
        overwrite or the variable going out of scope. Single backward pass
        per block, seeded from the sound `liveness()` live-out set, so this
        also catches redundant same-block overwrites (`x = 1; x = 2;` with
        no read of the first `1` in between), unlike Phase 3's
        last-reference-only heuristic."""
        live_out = self.liveness(cfg, graph)
        findings: list[dict[str, Any]] = []

        for block_id, block in cfg.blocks.items():
            events = self._block_events(block, graph)
            live_after = set(live_out.get(block_id, set()))
            for name, is_write, is_read_too, ref in reversed(events):
                reads_this_var = is_read_too or not is_write
                if is_write and not is_read_too:
                    if name not in live_after:
                        findings.append(ref)
                    live_after.discard(name)
                if reads_this_var:
                    live_after.add(name)
        return findings

    # ------------------------------------------------------------------
    # Taint propagation (forward)
    # ------------------------------------------------------------------

    def _taint_transfer(
        self,
        block: BasicBlock,
        incoming_tainted: set[str],
        graph: "AstGraph",
        sources: frozenset[str],
        sinks: frozenset[str],
        findings: list[TaintFinding] | None = None,
    ) -> set[str]:
        """Single linear scan of `block`, starting from `incoming_tainted`.
        Returns the tainted-variable set at the end of the block. If
        `findings` is passed, also appends every tainted-argument-reaches-sink
        occurrence found along the way — used as the one and only place sink
        findings are collected, so this must only be called with a *final*,
        already-converged `incoming_tainted` when collecting findings (see
        `propagate_taint`), to avoid reporting non-fixed-point intermediate
        results."""
        tainted = set(incoming_tainted)
        for statement in block.statements:
            nodes = self._statement_own_descendants(statement, graph)
            for node in nodes:
                if (
                    node.get("node_kind") == "BinaryOperator"
                    and node.get("semantic_properties", {}).get("opcode") == "="
                ):
                    children = graph.children(node["node_id"])
                    if len(children) >= 2:
                        lhs_name = self._decl_ref_name(children[0])
                        rhs = children[1]
                        rhs_descendants = [rhs, *graph.descendants(rhs["node_id"])]
                        is_tainted_source = any(
                            n.get("node_kind") == "CallExpr"
                            and n.get("semantic_properties", {}).get("callee", "") in sources
                            for n in rhs_descendants
                        )
                        reads_tainted_var = any(
                            n.get("node_kind") == "DeclRefExpr" and self._decl_ref_name(n) in tainted
                            for n in rhs_descendants
                        )
                        if lhs_name:
                            if is_tainted_source or reads_tainted_var:
                                tainted.add(lhs_name)
                            else:
                                tainted.discard(lhs_name)

                if node.get("node_kind") == "CallExpr":
                    callee = node.get("semantic_properties", {}).get("callee", "")
                    if callee in sinks and findings is not None:
                        for arg in graph.children(node["node_id"]):
                            arg_name = self._decl_ref_name(arg)
                            if arg_name and arg_name in tainted:
                                findings.append(
                                    TaintFinding(
                                        sink_call_node_id=node["node_id"],
                                        sink_function_name=callee,
                                        tainted_argument=arg_name,
                                        source_description=(
                                            f"'{arg_name}' is tainted by a designated source "
                                            "on every path reaching this call"
                                        ),
                                    )
                                )
        return tainted

    def propagate_taint(
        self,
        function_node: dict[str, Any],
        cfg: ControlFlowGraph,
        graph: "AstGraph",
        *,
        sources: frozenset[str] = _DEFAULT_TAINT_SOURCES,
        sinks: frozenset[str] = _DEFAULT_TAINT_SINKS,
    ) -> list[TaintFinding]:
        """Forward may-taint dataflow: `OUT[B] = transfer(B, IN[B])`,
        `IN[B] = union(OUT[P] for P in preds(B))`, iterated to a fixed
        point. Findings are collected in one final pass over the converged
        `IN` sets, so a sink is only reported once its tainted argument is
        confirmed reachable on some fully-resolved path — no separate
        gen/kill approximation and no double-counting between an
        intra-block pass and a cross-block pass."""
        block_ids = list(cfg.blocks.keys())
        out_sets: dict[str, set[str]] = {block_id: set() for block_id in block_ids}

        changed = True
        while changed:
            changed = False
            for block_id in block_ids:
                incoming = self._taint_in_set(block_id, cfg, out_sets)
                new_out = self._taint_transfer(
                    cfg.blocks[block_id], incoming, graph, sources, sinks, findings=None
                )
                if new_out != out_sets[block_id]:
                    out_sets[block_id] = new_out
                    changed = True

        findings: list[TaintFinding] = []
        for block_id in block_ids:
            incoming = self._taint_in_set(block_id, cfg, out_sets)
            self._taint_transfer(cfg.blocks[block_id], incoming, graph, sources, sinks, findings=findings)
        return findings

    def _taint_in_set(
        self, block_id: str, cfg: ControlFlowGraph, out_sets: dict[str, set[str]]
    ) -> set[str]:
        incoming: set[str] = set()
        for edge in cfg.predecessors(block_id):
            incoming |= out_sets.get(edge.source, set())
        return incoming

    # ------------------------------------------------------------------
    # Path-sensitive null-check facts
    # ------------------------------------------------------------------

    def null_check_facts(self, cfg: ControlFlowGraph, graph: "AstGraph") -> list[NullCheckFact]:
        facts: list[NullCheckFact] = []
        for block_id, block in cfg.blocks.items():
            for statement in block.statements:
                if statement.get("node_kind") != "IfStmt":
                    continue
                children = graph.children(statement["node_id"])
                if not children:
                    continue
                condition = children[0]
                parsed = self._parse_null_check(condition, graph)
                if parsed is None:
                    continue
                var_name, null_when_true = parsed
                for edge in cfg.successors(block_id):
                    if edge.kind == "true":
                        facts.append(
                            NullCheckFact(edge.target, var_name, "null" if null_when_true else "non_null")
                        )
                    elif edge.kind == "false":
                        facts.append(
                            NullCheckFact(edge.target, var_name, "non_null" if null_when_true else "null")
                        )
        return facts

    def _parse_null_check(
        self, condition: dict[str, Any], graph: "AstGraph"
    ) -> tuple[str, bool] | None:
        """Recognizes `ptr == NULL`/`ptr != NULL`/`ptr`/`!ptr` shapes.
        Returns (variable_name, null_when_true)."""
        kind = condition.get("node_kind")
        if kind == "UnaryOperator" and condition.get("semantic_properties", {}).get("opcode") == "!":
            children = graph.children(condition["node_id"])
            if children and children[0].get("node_kind") == "DeclRefExpr":
                return self._decl_ref_name(children[0]), True
            return None
        if kind == "DeclRefExpr":
            return self._decl_ref_name(condition), False
        if kind == "BinaryOperator":
            opcode = condition.get("semantic_properties", {}).get("opcode", "")
            if opcode not in ("==", "!="):
                return None
            children = graph.children(condition["node_id"])
            if len(children) < 2:
                return None
            lhs, rhs = children[0], children[1]
            var_side = lhs if lhs.get("node_kind") == "DeclRefExpr" else rhs
            other_side = rhs if var_side is lhs else lhs
            if var_side.get("node_kind") != "DeclRefExpr":
                return None
            other_value = str(other_side.get("semantic_properties", {}).get("value", ""))
            is_null_literal = other_side.get("node_kind") == "IntegerLiteral" and other_value in ("0", "0x0", "NULL")
            if not is_null_literal:
                return None
            return self._decl_ref_name(var_side), opcode == "=="
        return None

    # ------------------------------------------------------------------
    # Variable lifetime ranges
    # ------------------------------------------------------------------

    def variable_lifetime_ranges(
        self, function_node: dict[str, Any], graph: "AstGraph"
    ) -> list[LifetimeRange]:
        """Approximates each automatic variable's lifetime as the AST-scope
        range of its nearest enclosing `CompoundStmt` (its C block scope),
        from the declaration's line to the scope's last statement's line.
        This is scope-based (AST), not CFG-block-based, since the CFG here
        doesn't model scope-exit as a distinct construct — see module docstring.
        """
        ranges: list[LifetimeRange] = []
        for node in graph.descendants(function_node["node_id"]):
            if node.get("node_kind") != "VarDecl":
                continue
            name = self._decl_ref_name(node)
            if not name:
                continue
            scope = graph.get(node.get("parent_id", ""))
            if scope is None:
                continue
            siblings = graph.children(scope["node_id"])
            lines = [
                s.get("source_range", {}).get("line_end", 0)
                for s in siblings
                if s.get("source_range")
            ]
            decl_line = node.get("source_range", {}).get("line_start", 0)
            ranges.append(
                LifetimeRange(
                    variable=name,
                    decl_node_id=node["node_id"],
                    scope_node_id=scope["node_id"],
                    first_line=decl_line,
                    last_line=max(lines) if lines else decl_line,
                )
            )
        return ranges

    def escapes_lifetime(
        self,
        lifetime: LifetimeRange,
        use_node: dict[str, Any],
    ) -> bool:
        use_line = use_node.get("source_range", {}).get("line_start", 0)
        return use_line > lifetime.last_line
