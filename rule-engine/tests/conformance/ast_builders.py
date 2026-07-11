"""Minimal synthetic-AST builder used to construct conformance fixtures
without hand-writing repetitive node dictionaries."""

from typing import Any


class Builder:
    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.preprocessor: dict[str, Any] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def _by_id(self, node_id: str) -> dict[str, Any]:
        return next(n for n in self.nodes if n["node_id"] == node_id)

    def node(self, kind: str, parent: str | None = None, line: int | None = None, **kwargs: Any) -> str:
        node_id = self._next_id()
        line_number = line if line is not None else len(self.nodes) + 1
        payload: dict[str, Any] = {
            "node_id": node_id,
            "node_kind": kind,
            "parent_id": parent or "",
            "children_ids": [],
            "source_range": kwargs.pop(
                "source_range",
                {
                    "file_path": "demo.c",
                    "line_start": line_number,
                    "line_end": line_number,
                    "column_start": 1,
                    "column_end": 10,
                },
            ),
            "type_information": kwargs.pop("type_information", {}),
            "qualifiers": kwargs.pop("qualifiers", []),
            "essential_type": kwargs.pop("essential_type", "unknown"),
            "macro_origin": kwargs.pop("macro_origin", {}),
            "semantic_properties": kwargs.pop("semantic_properties", {}),
        }
        payload.update(kwargs)
        self.nodes.append(payload)
        if parent:
            self._by_id(parent)["children_ids"].append(node_id)
        return node_id

    def artifact(self, file_path: str = "demo.c") -> dict[str, Any]:
        return {
            "file_path": file_path,
            "nodes": self.nodes,
            "diagnostics": [],
            "preprocessor": self.preprocessor,
        }
