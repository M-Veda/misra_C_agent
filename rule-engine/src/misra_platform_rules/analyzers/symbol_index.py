"""Shared infrastructure for the Declarations, Storage Duration, and Linkage
packs: an index of every named declaration in a translation unit."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_DECL_KINDS = {
    "VarDecl",
    "FunctionDecl",
    "TypedefDecl",
    "EnumDecl",
    "RecordDecl",
    "ParmVarDecl",
    "FieldDecl",
}

# C has separate identifier namespaces: tags (struct/union/enum names),
# members (struct/union field names, scoped per-aggregate), and "ordinary"
# identifiers (everything else: objects, functions, typedefs, enum
# constants). Two declarations with the same spelling only collide in the
# MISRA 5.2 sense if they fall in *different* namespaces.
_TAG_KINDS = {"RecordDecl", "EnumDecl"}
_MEMBER_KINDS = {"FieldDecl"}


def _namespace(node: dict[str, Any]) -> str:
    kind = node.get("node_kind")
    if kind in _TAG_KINDS:
        return "tag"
    if kind in _MEMBER_KINDS:
        return "member"
    return "ordinary"


class SymbolIndex:
    def __init__(self, graph: "AstGraph") -> None:
        self.graph = graph
        self._by_name: dict[str, list[dict[str, Any]]] = {}
        for node in graph.all_nodes():
            if node.get("node_kind") not in _DECL_KINDS:
                continue
            name = node.get("semantic_properties", {}).get("name", "")
            if not name:
                continue
            self._by_name.setdefault(name, []).append(node)

    def all_names(self) -> list[str]:
        return list(self._by_name.keys())

    def declarations(self, name: str) -> list[dict[str, Any]]:
        return self._by_name.get(name, [])

    def storage_class(self, node: dict[str, Any]) -> str:
        return node.get("semantic_properties", {}).get("storage_class", "automatic")

    def is_external_linkage(self, node: dict[str, Any]) -> bool:
        if self.storage_class(node) == "static":
            return False
        return self.graph.is_file_scope(node["node_id"])

    def is_internal_linkage(self, node: dict[str, Any]) -> bool:
        return self.storage_class(node) == "static" and self.graph.is_file_scope(node["node_id"])

    def duplicate_names_within(self, significant_chars: int) -> list[tuple[str, str]]:
        """Pairs of distinct identifiers that collide within the first
        `significant_chars` characters — MISRA Rule 5.1/5.2 style checks."""
        truncated: dict[str, list[str]] = {}
        for name in self._by_name:
            key = name[:significant_chars]
            truncated.setdefault(key, []).append(name)

        collisions: list[tuple[str, str]] = []
        for names in truncated.values():
            unique = sorted(set(names))
            if len(unique) > 1:
                for i, first in enumerate(unique):
                    for second in unique[i + 1 :]:
                        collisions.append((first, second))
        return collisions

    def cross_namespace_collisions(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """(first, second) declaration pairs sharing a spelling across two
        *different* C identifier namespaces — MISRA Rule 5.2 style checks.
        Same-namespace same-scope redeclaration is generally a compiler error
        already, so this focuses on the genuinely MISRA-specific case."""
        collisions: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for decls in self._by_name.values():
            if len(decls) < 2:
                continue
            for i, first in enumerate(decls):
                for second in decls[i + 1 :]:
                    if _namespace(first) != _namespace(second):
                        collisions.append((first, second))
        return collisions

    def is_referenced(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        """True if `node` is used anywhere else in the graph.

        For ordinary-namespace value declarations (`VarDecl`/`ParmVarDecl`/
        `FunctionDecl`) that means a matching `DeclRefExpr`. For a type-name
        declaration (`TypedefDecl`, or a tag declaration `RecordDecl`/
        `EnumDecl` — MISRA Rules 2.3/2.4) there is no `DeclRefExpr`; instead
        any other declaration whose `semantic_properties.type_name` spells
        the same name is a use of it as a type."""
        name = node.get("semantic_properties", {}).get("name", "")
        if not name:
            return True  # can't prove non-use without a name; avoid false positives
        if node.get("node_kind") in ("TypedefDecl", "RecordDecl", "EnumDecl"):
            return self._is_type_referenced(node, name)
        for candidate in self.graph.nodes_by_kind("DeclRefExpr"):
            if candidate.get("node_id") == node.get("node_id"):
                continue
            if candidate.get("semantic_properties", {}).get("name") == name:
                return True
        return False

    def _is_type_referenced(self, node: dict[str, Any], name: str) -> bool:
        node_id = node.get("node_id")
        for candidate in self.graph.all_nodes():
            if candidate.get("node_id") == node_id:
                continue
            properties = candidate.get("semantic_properties", {})
            if properties.get("type_name") == name:
                return True
            type_info = candidate.get("type_information", {}) or {}
            if name and name in (type_info.get("typedef_chain") or ""):
                return True
        return False

    def shadowing_pairs(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """(outer, inner) declaration pairs that share a name across nested
        scopes. A declaration's *scope* is its `parent_id` (the statement/
        function/block that directly contains it) — an empty `parent_id`
        means file scope, which encloses every other scope. `first` shadows
        `second` when `first`'s scope is file scope, or is a strict
        ancestor of `second`'s own scope (walking `second`'s node path)."""
        pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for decls in self._by_name.values():
            if len(decls) < 2:
                continue
            for i, first in enumerate(decls):
                for second in decls[i + 1 :]:
                    pair = self._order_by_enclosing_scope(first, second)
                    if pair is not None:
                        pairs.append(pair)
        return pairs

    def _order_by_enclosing_scope(
        self, first: dict[str, Any], second: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        first_scope = first.get("parent_id", "")
        second_scope = second.get("parent_id", "")
        if first_scope == second_scope:
            return None  # same scope: a redeclaration, not shadowing

        first_is_file_scope = not first_scope
        second_is_file_scope = not second_scope
        if first_is_file_scope and not second_is_file_scope:
            return (first, second)
        if second_is_file_scope and not first_is_file_scope:
            return (second, first)

        second_path = self.graph.node_path(second["node_id"])
        if first_scope and first_scope in second_path:
            return (first, second)
        first_path = self.graph.node_path(first["node_id"])
        if second_scope and second_scope in first_path:
            return (second, first)
        return None
