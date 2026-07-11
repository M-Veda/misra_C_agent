"""Category D shared infrastructure: best-effort intra-procedural data flow.

Without a real CFG with basic blocks (see `CFGBuilder`), this engine performs
a *textual-order* approximation of reaching definitions: it linearizes AST
nodes by source position and classifies each variable reference as a read or
a write based on its immediate parent. This is deliberately conservative
(prefers false negatives over false positives across branches/loops) and is
documented as a known limitation rather than a sound dataflow analysis.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph


class DataFlowEngine:
    def _linearize(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(node: dict[str, Any]) -> tuple[int, int]:
            source_range = node.get("source_range", {})
            return (source_range.get("line_start", 0), source_range.get("column_start", 0))

        return sorted(nodes, key=sort_key)

    def _is_write_target(self, decl_ref: dict[str, Any], graph: "AstGraph") -> bool:
        parent = graph.get(decl_ref.get("parent_id", ""))
        if not parent:
            return False
        if parent.get("node_kind") == "BinaryOperator":
            opcode = parent.get("semantic_properties", {}).get("opcode", "")
            if opcode.endswith("=") and opcode != "==" and opcode != "!=":
                children = graph.children(parent["node_id"])
                return bool(children) and children[0].get("node_id") == decl_ref.get("node_id")
        if parent.get("node_kind") == "UnaryOperator":
            opcode = parent.get("semantic_properties", {}).get("opcode", "")
            return opcode in ("++", "--")
        return False

    def local_variable_declarations(
        self, function_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        return [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "VarDecl"
        ]

    def has_initializer(self, var_decl: dict[str, Any], graph: "AstGraph") -> bool:
        children = graph.children(var_decl["node_id"])
        return any(
            child.get("node_kind") not in ("BuiltinType", "RecordType", "PointerType")
            for child in children
        )

    def references(
        self, var_decl: dict[str, Any], function_node: dict[str, Any], graph: "AstGraph"
    ) -> list[dict[str, Any]]:
        name = var_decl.get("semantic_properties", {}).get("name", "")
        if not name:
            return []
        candidates = [
            node
            for node in graph.descendants(function_node["node_id"])
            if node.get("node_kind") == "DeclRefExpr"
            and node.get("semantic_properties", {}).get("name") == name
        ]
        return self._linearize(candidates)

    def uninitialized_read(
        self, var_decl: dict[str, Any], function_node: dict[str, Any], graph: "AstGraph"
    ) -> dict[str, Any] | None:
        """First read of `var_decl` that occurs before any write, when the
        declaration itself has no initializer."""
        if self.has_initializer(var_decl, graph):
            return None
        for reference in self.references(var_decl, function_node, graph):
            if self._is_write_target(reference, graph):
                return None
            return reference
        return None

    def dead_store(
        self, var_decl: dict[str, Any], function_node: dict[str, Any], graph: "AstGraph"
    ) -> dict[str, Any] | None:
        """Last reference to `var_decl` is a write that nothing subsequently reads."""
        references = self.references(var_decl, function_node, graph)
        if not references:
            return None
        last = references[-1]
        if self._is_write_target(last, graph):
            return last
        return None
