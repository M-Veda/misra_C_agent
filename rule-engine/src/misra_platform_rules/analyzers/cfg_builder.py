"""Category C shared infrastructure: structural control-flow analysis.

The serialized AST does not carry an explicit CFG (basic blocks / edges) from
clang-worker. This builder produces a *structural approximation* of the
control-flow facts MISRA control-flow rules need (exit points, unreachable
statements, switch fallthrough, nesting depth) directly from the AST tree
shape. This is intentionally documented as an approximation, not a sound
dataflow-grade CFG — see Phase 3 known limitations.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_UNCONDITIONAL_TERMINATORS = {"ReturnStmt", "BreakStmt", "ContinueStmt", "GotoStmt"}
_LOOP_KINDS = {"ForStmt", "WhileStmt", "DoStmt"}
_BRANCH_KINDS = {"IfStmt", "SwitchStmt"}


class CFGBuilder:
    def exit_points(self, function_node: dict[str, Any], graph: "AstGraph") -> list[dict[str, Any]]:
        return [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "ReturnStmt"
        ]

    def has_single_exit(self, function_node: dict[str, Any], graph: "AstGraph") -> bool:
        return len(self.exit_points(function_node, graph)) <= 1

    def unreachable_statements(
        self, function_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        """Statements structurally following an unconditional terminator in the
        same compound block, with no intervening label (goto target)."""
        unreachable: list[dict[str, Any]] = []
        for block in [function_node, *graph.descendants(function_node["node_id"])]:
            if block.get("node_kind") != "CompoundStmt":
                continue
            children = graph.children(block["node_id"])
            terminated = False
            for child in children:
                if terminated:
                    if child.get("node_kind") == "LabelStmt":
                        terminated = False
                    else:
                        unreachable.append(child)
                        continue
                if child.get("node_kind") in _UNCONDITIONAL_TERMINATORS:
                    terminated = True
        return unreachable

    def nesting_depth(self, node: dict[str, Any], graph: "AstGraph") -> int:
        depth = 0
        current_id = node.get("parent_id", "")
        while current_id:
            parent = graph.get(current_id)
            if not parent:
                break
            if parent.get("node_kind") in _LOOP_KINDS | _BRANCH_KINDS:
                depth += 1
            current_id = parent.get("parent_id", "")
        return depth

    def switch_is_malformed(self, switch_node: dict[str, Any], graph: "AstGraph") -> bool:
        """MISRA Rule 16.1: a switch without a compound-statement body, with
        no switch clauses, or explicitly flagged as malformed."""
        if switch_node.get("semantic_properties", {}).get("switch_malformed"):
            return True
        body_candidates = [
            child
            for child in graph.children(switch_node["node_id"])
            if child.get("node_kind") == "CompoundStmt"
        ]
        if not body_candidates:
            return True
        return self.switch_has_no_clauses(switch_node, graph)

    def switch_has_no_clauses(self, switch_node: dict[str, Any], graph: "AstGraph") -> bool:
        body_candidates = [
            child
            for child in graph.children(switch_node["node_id"])
            if child.get("node_kind") == "CompoundStmt"
        ]
        if not body_candidates:
            return True
        body = body_candidates[0]
        return not any(
            child.get("node_kind") in ("CaseStmt", "DefaultStmt")
            for child in graph.children(body["node_id"])
        )

    def switch_blocks_without_terminator(
        self, switch_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        """CaseStmt/DefaultStmt nodes whose block falls through to the next
        case without an explicit break/return/continue/goto — MISRA 16.x."""
        body_candidates = [
            child for child in graph.children(switch_node["node_id"]) if child.get("node_kind") == "CompoundStmt"
        ]
        if not body_candidates:
            return []
        body = body_candidates[0]
        statements = graph.children(body["node_id"])

        fallthrough: list[dict[str, Any]] = []
        pending_case: dict[str, Any] | None = None
        saw_terminator_since_case = True

        for statement in statements:
            kind = statement.get("node_kind")
            if kind in ("CaseStmt", "DefaultStmt"):
                if pending_case is not None and not saw_terminator_since_case:
                    fallthrough.append(pending_case)
                pending_case = statement
                saw_terminator_since_case = False
                continue
            if kind in _UNCONDITIONAL_TERMINATORS:
                saw_terminator_since_case = True

        if pending_case is not None and not saw_terminator_since_case:
            fallthrough.append(pending_case)
        return fallthrough

    def loop_termination_statements(
        self, loop_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        """BreakStmt/GotoStmt nodes that terminate `loop_node` directly —
        i.e. found in its body without crossing into a nested loop or
        switch's own body (whose own break/goto terminates *that* nested
        construct instead) — MISRA Rule 15.4."""
        terminators: list[dict[str, Any]] = []

        def _walk(node: dict[str, Any], *, is_loop_root: bool) -> None:
            for child in graph.children(node["node_id"]):
                kind = child.get("node_kind")
                if kind in ("BreakStmt", "GotoStmt"):
                    terminators.append(child)
                    continue
                if not is_loop_root and kind in _LOOP_KINDS | {"SwitchStmt"}:
                    # A break inside a nested loop/switch terminates that
                    # nested construct, not this loop — do not descend.
                    continue
                _walk(child, is_loop_root=False)

        _walk(loop_node, is_loop_root=True)
        return terminators

    def goto_targets(self, function_node: dict[str, Any], graph: "AstGraph") -> list[dict[str, Any]]:
        return [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "GotoStmt"
        ]

    def labels(self, function_node: dict[str, Any], graph: "AstGraph") -> list[dict[str, Any]]:
        return [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "LabelStmt"
        ]
