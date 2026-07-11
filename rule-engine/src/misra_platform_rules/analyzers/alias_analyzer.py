"""Phase 4: intra-procedural points-to / alias analysis.

Builds a flow-insensitive (whole-function, not per-CFG-block) points-to map
by a single linear scan of every pointer-producing assignment/initializer in
a function: address-of (`p = &x`), pointer copy (`p = q`), array-to-pointer
decay (`p = arr`), function-pointer capture (`fp = &f` / `fp = f`), and
"escape hatches" that make the target unknowable from this function alone
(heap allocation, calls to opaque functions, incoming pointer parameters).

Flow-insensitivity means a points-to set accumulates every value a pointer
*could* hold at *any* point in the function (e.g. after `if (c) p = &x; else
p = &y;`, `points_to("p") == {x, y}`) — a sound over-approximation for "may
alias" queries, but not precise enough to say what `p` points to at one
specific program point (that would need a per-CFG-block points-to dataflow,
noted as a known limitation in Phase 4 docs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

CONFIDENCE_DEFINITE = "definite"
CONFIDENCE_POSSIBLE = "possible"
CONFIDENCE_UNKNOWN = "unknown"

_CONFIDENCE_RANK = {CONFIDENCE_DEFINITE: 2, CONFIDENCE_POSSIBLE: 1, CONFIDENCE_UNKNOWN: 0}

UNKNOWN_TARGET = "<unknown>"


@dataclass(slots=True, frozen=True)
class Pointee:
    target: str
    kind: str  # "variable" | "array" | "function" | "heap" | "unknown"
    confidence: str  # definite | possible | unknown

    def __hash__(self) -> int:
        return hash((self.target, self.kind, self.confidence))


class AliasAnalyzer:
    def __init__(self) -> None:
        self._points_to: dict[str, set[Pointee]] = {}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def analyze(self, function_node: dict[str, Any], graph: "AstGraph") -> "AliasAnalyzer":
        """Populates and returns `self` so callers can chain
        `AliasAnalyzer().analyze(fn, graph)`.

        Processes relevant statements in *source order* (not AST-traversal
        order — `AstGraph.descendants` is a DFS via an explicit stack and
        does not guarantee source order) and iterates to a fixed point:
        points-to sets only ever grow (monotonic), so a pass that adds
        nothing new means convergence. This is required for straight-line
        pointer chains (`p = &x; q = p;`) to resolve correctly regardless of
        AST child ordering, and for chains that depend on a later statement
        (e.g. inside loops) to still be captured."""
        self._points_to = {}
        self._seed_pointer_parameters(function_node, graph)

        relevant = [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "VarDecl"
            or (
                node.get("node_kind") == "BinaryOperator"
                and node.get("semantic_properties", {}).get("opcode") == "="
            )
        ]
        relevant = self._linearize(relevant)

        for _ in range(len(relevant) + 1):
            before = {name: frozenset(pointees) for name, pointees in self._points_to.items()}
            for node in relevant:
                if node.get("node_kind") == "VarDecl":
                    self._handle_var_decl(node, graph)
                else:
                    self._handle_assignment(node, graph)
            after = {name: frozenset(pointees) for name, pointees in self._points_to.items()}
            if after == before:
                break
        return self

    def _linearize(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(node: dict[str, Any]) -> tuple[int, int]:
            source_range = node.get("source_range", {})
            return (source_range.get("line_start", 0), source_range.get("column_start", 0))

        return sorted(nodes, key=sort_key)

    def _seed_pointer_parameters(self, function_node: dict[str, Any], graph: "AstGraph") -> None:
        for node in graph.children(function_node["node_id"]):
            if node.get("node_kind") != "ParmVarDecl":
                continue
            if not node.get("type_information", {}).get("is_pointer", False):
                continue
            name = node.get("semantic_properties", {}).get("name", "")
            if name:
                self._points_to.setdefault(name, set()).add(
                    Pointee(UNKNOWN_TARGET, "unknown", CONFIDENCE_UNKNOWN)
                )

    def _handle_var_decl(self, node: dict[str, Any], graph: "AstGraph") -> None:
        name = node.get("semantic_properties", {}).get("name", "")
        if not name or not node.get("type_information", {}).get("is_pointer", False):
            return
        children = graph.children(node["node_id"])
        initializer = next(
            (c for c in children if c.get("node_kind") not in ("BuiltinType", "PointerType", "RecordType")),
            None,
        )
        if initializer is None:
            return
        for pointee in self._resolve_rhs(initializer, graph):
            self._points_to.setdefault(name, set()).add(pointee)

    def _handle_assignment(self, node: dict[str, Any], graph: "AstGraph") -> None:
        children = graph.children(node["node_id"])
        if len(children) < 2:
            return
        lhs, rhs = children[0], children[1]
        if lhs.get("node_kind") != "DeclRefExpr":
            return
        name = lhs.get("semantic_properties", {}).get("name", "")
        if not name:
            return
        for pointee in self._resolve_rhs(rhs, graph):
            self._points_to.setdefault(name, set()).add(pointee)

    def _resolve_rhs(self, rhs: dict[str, Any], graph: "AstGraph") -> list[Pointee]:
        kind = rhs.get("node_kind")

        if kind == "UnaryOperator" and rhs.get("semantic_properties", {}).get("opcode") == "&":
            operand = next(iter(graph.children(rhs["node_id"])), None)
            if operand is not None and operand.get("node_kind") == "DeclRefExpr":
                target = operand.get("semantic_properties", {}).get("name", "")
                target_kind = "function" if operand.get("semantic_properties", {}).get(
                    "is_function", False
                ) else "variable"
                if target:
                    return [Pointee(target, target_kind, CONFIDENCE_DEFINITE)]
            return [Pointee(UNKNOWN_TARGET, "unknown", CONFIDENCE_UNKNOWN)]

        if kind == "DeclRefExpr":
            name = rhs.get("semantic_properties", {}).get("name", "")
            if rhs.get("semantic_properties", {}).get("is_function", False):
                return [Pointee(name, "function", CONFIDENCE_DEFINITE)] if name else []
            if rhs.get("type_information", {}).get("is_array", False):
                return [Pointee(name, "array", CONFIDENCE_DEFINITE)] if name else []
            if name in self._points_to:
                # Pointer-to-pointer copy: inherit the RHS's current
                # points-to set. If the RHS set has more than one member
                # (came from a branch merge) or is already non-definite,
                # downgrade confidence one notch to reflect the added
                # indirection, matching how real alias uncertainty compounds.
                existing = self._points_to[name]
                downgrade = len(existing) > 1
                resolved = []
                for pointee in existing:
                    new_confidence = pointee.confidence
                    if downgrade and new_confidence == CONFIDENCE_DEFINITE:
                        new_confidence = CONFIDENCE_POSSIBLE
                    resolved.append(Pointee(pointee.target, pointee.kind, new_confidence))
                return resolved
            # DeclRefExpr to something we have no pointer-origin info for
            # (e.g. it's itself a parameter we haven't seeded, or a scalar
            # mistakenly assigned — be conservative rather than silent).
            return [Pointee(UNKNOWN_TARGET, "unknown", CONFIDENCE_UNKNOWN)]

        if kind == "CallExpr":
            # Heap allocation or any opaque function call: a fresh/unknown
            # address every call, so it cannot alias any *named* local —
            # but callers should still treat it conservatively for sink
            # analysis, hence "unknown" rather than dropping it silently.
            callee = rhs.get("semantic_properties", {}).get("callee", "")
            return [Pointee(f"<heap:{callee}>", "heap", CONFIDENCE_POSSIBLE)]

        return []

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def points_to(self, name: str) -> set[Pointee]:
        return set(self._points_to.get(name, set()))

    def may_alias(self, a: str, b: str) -> tuple[bool, str]:
        """Returns (may_alias, confidence). Two pointers may alias if their
        points-to sets share a named target, or if either is unknown
        (conservative: cannot rule out aliasing)."""
        set_a = self._points_to.get(a, set())
        set_b = self._points_to.get(b, set())
        if not set_a or not set_b:
            return False, CONFIDENCE_UNKNOWN

        if any(p.kind == "unknown" for p in set_a) or any(p.kind == "unknown" for p in set_b):
            return True, CONFIDENCE_UNKNOWN

        shared_targets = {p.target for p in set_a} & {p.target for p in set_b}
        if not shared_targets:
            return False, CONFIDENCE_DEFINITE

        best_confidence = CONFIDENCE_UNKNOWN
        for target in shared_targets:
            for pointee in (*set_a, *set_b):
                if pointee.target == target:
                    if _CONFIDENCE_RANK[pointee.confidence] > _CONFIDENCE_RANK[best_confidence]:
                        best_confidence = pointee.confidence
        is_definite_alias = (
            len(set_a) == 1
            and len(set_b) == 1
            and next(iter(set_a)).confidence == CONFIDENCE_DEFINITE
            and next(iter(set_b)).confidence == CONFIDENCE_DEFINITE
        )
        return True, CONFIDENCE_DEFINITE if is_definite_alias else CONFIDENCE_POSSIBLE

    def pointer_aliases(self) -> list[tuple[str, Pointee]]:
        return [
            (name, pointee)
            for name, pointees in self._points_to.items()
            for pointee in pointees
            if pointee.kind == "variable"
        ]

    def array_aliases(self) -> list[tuple[str, Pointee]]:
        return [
            (name, pointee)
            for name, pointees in self._points_to.items()
            for pointee in pointees
            if pointee.kind == "array"
        ]

    def function_pointer_aliases(self) -> list[tuple[str, Pointee]]:
        return [
            (name, pointee)
            for name, pointees in self._points_to.items()
            for pointee in pointees
            if pointee.kind == "function"
        ]

    def all_pointer_names(self) -> list[str]:
        return list(self._points_to.keys())
