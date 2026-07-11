"""Category E shared infrastructure: cross-translation-unit linkage facts.

`LinkageIndex.build()` is called ONCE per analysis run (by the backend's
`RuleDispatcher`, across every translation unit's AST), producing a plain
JSON-serializable dict that is then attached to every `RuleContext` as
`cross_tu_linkage`. Rules never build this themselves — it requires
whole-project information a single-TU rule cannot see.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_DEFINITION_KINDS = {"FunctionDecl", "VarDecl"}


class LinkageIndex:
    @staticmethod
    def build(units: list[tuple[str, str, "AstGraph"]]) -> dict[str, Any]:
        symbols: dict[str, list[dict[str, Any]]] = {}

        for translation_unit_id, file_path, graph in units:
            for kind in _DEFINITION_KINDS:
                for node in graph.nodes_by_kind(kind):
                    name = node.get("semantic_properties", {}).get("name", "")
                    if not name or not graph.is_file_scope(node["node_id"]):
                        continue
                    storage_class = node.get("semantic_properties", {}).get(
                        "storage_class", "external"
                    )
                    has_body = kind == "FunctionDecl" and any(
                        child.get("node_kind") == "CompoundStmt"
                        for child in graph.children(node["node_id"])
                    )
                    symbols.setdefault(name, []).append(
                        {
                            "translation_unit_id": translation_unit_id,
                            "file_path": file_path,
                            "storage_class": storage_class,
                            "has_body": has_body,
                            "type_spelling": node.get("type_information", {}).get("spelling", ""),
                            "node_kind": kind,
                        }
                    )

        call_graph: dict[str, list[str]] = {}
        for _translation_unit_id, _file_path, graph in units:
            for func in graph.nodes_by_kind("FunctionDecl"):
                name = func.get("semantic_properties", {}).get("name", "")
                if not name:
                    continue
                has_body = any(
                    child.get("node_kind") == "CompoundStmt"
                    for child in graph.children(func["node_id"])
                )
                if not has_body:
                    continue
                callees: list[str] = []
                for node in graph.descendants(func["node_id"]):
                    if node.get("node_kind") != "CallExpr":
                        continue
                    callee = node.get("semantic_properties", {}).get("callee", "")
                    if callee and callee not in callees:
                        callees.append(callee)
                if callees:
                    existing = call_graph.setdefault(name, [])
                    for callee in callees:
                        if callee not in existing:
                            existing.append(callee)

        return {"symbols": symbols, "call_graph": call_graph}

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {"symbols": {}, "call_graph": {}}

    def occurrences(self, name: str) -> list[dict[str, Any]]:
        return self.data.get("symbols", {}).get(name, [])

    def external_occurrences(self, name: str) -> list[dict[str, Any]]:
        return [o for o in self.occurrences(name) if o["storage_class"] != "static"]

    def definitions(self, name: str) -> list[dict[str, Any]]:
        return [o for o in self.external_occurrences(name) if o["has_body"]]

    def has_multiple_definitions(self, name: str) -> bool:
        # Count distinct translation units defining the symbol with a body.
        tus = {o["translation_unit_id"] for o in self.definitions(name)}
        return len(tus) > 1

    def incompatible_type_spellings(self, name: str) -> list[tuple[str, str]]:
        spellings = {o["type_spelling"] for o in self.external_occurrences(name) if o["type_spelling"]}
        if len(spellings) <= 1:
            return []
        ordered = sorted(spellings)
        return [(ordered[i], ordered[j]) for i in range(len(ordered)) for j in range(i + 1, len(ordered))]

    def all_names(self) -> list[str]:
        return list(self.data.get("symbols", {}).keys())

    def single_translation_unit(self, name: str) -> str | None:
        """The single TU that references/defines `name`, if there is exactly one."""
        tus = {o["translation_unit_id"] for o in self.occurrences(name)}
        if len(tus) == 1:
            return next(iter(tus))
        return None

    def internal_linkage_occurrences(self, name: str) -> list[dict[str, Any]]:
        return [o for o in self.occurrences(name) if o["storage_class"] == "static"]

    def internal_linkage_translation_units(self, name: str) -> set[str]:
        return {o["translation_unit_id"] for o in self.internal_linkage_occurrences(name)}

    def non_defining_external_translation_units(self, name: str) -> set[str]:
        """Translation units that carry a non-defining (declaration-only)
        external-linkage occurrence of `name` — MISRA Rule 8.5 territory:
        a prototype re-typed in more than one file instead of shared via a
        single header."""
        return {o["translation_unit_id"] for o in self.external_occurrences(name) if not o["has_body"]}

    def call_graph(self) -> dict[str, list[str]]:
        return self.data.get("call_graph", {})

    def functions_in_recursion_cycles(self) -> list[str]:
        """Return every function name that participates in a direct or indirect
        recursion cycle according to `call_graph`."""
        graph = self.call_graph()
        if not graph:
            return []

        index = 0
        indices: dict[str, int] = {}
        lowlink: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        cycles: list[set[str]] = []

        def strongconnect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for callee in graph.get(node, []):
                if callee not in indices:
                    strongconnect(callee)
                    lowlink[node] = min(lowlink[node], lowlink[callee])
                elif callee in on_stack:
                    lowlink[node] = min(lowlink[node], indices[callee])

            if lowlink[node] == indices[node]:
                component: set[str] = set()
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.add(w)
                    if w == node:
                        break
                if len(component) > 1 or (len(component) == 1 and node in graph.get(node, [])):
                    cycles.append(component)

        for name in graph:
            if name not in indices:
                strongconnect(name)

        in_cycle = set().union(*cycles) if cycles else set()
        return sorted(in_cycle)

    def duplicate_names_within(self, significant_chars: int) -> list[tuple[str, str]]:
        """Cross-TU counterpart of `SymbolIndex.duplicate_names_within` — pairs
        of distinct external identifiers colliding within the first
        `significant_chars` characters, considering every translation unit."""
        truncated: dict[str, list[str]] = {}
        for name in self.all_names():
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
