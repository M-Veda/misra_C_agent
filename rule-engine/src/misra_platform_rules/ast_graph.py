from typing import Any

from misra_platform_rules.rule_context import RuleContext


class AstGraph:
    def __init__(self, nodes: list[dict[str, Any]]) -> None:
        self._nodes = {node["node_id"]: node for node in nodes}
        self._nodes_list = nodes

    def get(self, node_id: str) -> dict[str, Any] | None:
        return self._nodes.get(node_id)

    def all_nodes(self) -> list[dict[str, Any]]:
        return self._nodes_list

    def nodes_by_kind(self, kind: str) -> list[dict[str, Any]]:
        return [node for node in self._nodes_list if node.get("node_kind") == kind]

    def children(self, node_id: str) -> list[dict[str, Any]]:
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [
            self._nodes[child_id]
            for child_id in node.get("children_ids", [])
            if child_id in self._nodes
        ]

    def descendants(self, node_id: str) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        stack = list(self.children(node_id))
        while stack:
            current = stack.pop()
            collected.append(current)
            stack.extend(self.children(current["node_id"]))
        return collected

    def node_path(self, node_id: str) -> list[str]:
        path: list[str] = []
        current_id: str | None = node_id
        while current_id:
            path.append(current_id)
            parent = self._nodes.get(current_id, {}).get("parent_id", "")
            current_id = parent if parent else None
        return list(reversed(path))

    def is_file_scope(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        parent_id = node.get("parent_id", "")
        return not parent_id

    def essential_type_rank(self, essential_type: str) -> int:
        order = [
            "boolean",
            "signed_char",
            "unsigned_char",
            "char",
            "signed_short",
            "unsigned_short",
            "signed_int",
            "unsigned_int",
            "signed_long",
            "unsigned_long",
            "signed_long_long",
            "unsigned_long_long",
            "float",
            "double",
            "long_double",
            "complex",
            "unknown",
        ]
        try:
            return order.index(essential_type)
        except ValueError:
            return len(order)

    def source_snippet(self, context: RuleContext, node: dict[str, Any], radius: int = 2) -> str:
        line = node.get("source_range", {}).get("line_start", 0)
        return f"{context.file_path}:{line}"

    @staticmethod
    def offending_text(node: dict[str, Any]) -> str:
        name = node.get("semantic_properties", {}).get("name", "")
        kind = node.get("node_kind", "")
        essential = node.get("essential_type", "")
        type_spelling = node.get("type_information", {}).get("spelling", "")
        if name:
            return f"{kind} {name}"
        if type_spelling:
            return f"{kind} ({type_spelling})"
        return f"{kind} [{essential}]"
