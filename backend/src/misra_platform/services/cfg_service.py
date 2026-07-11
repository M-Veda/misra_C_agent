"""Phase 4 deliverable: CFG construction/visualization service.

Reuses the AST artifacts already cached to disk by the analysis pipeline
(see `LocalArtifactStorage`/`analysis_orchestrator.py`) rather than
re-parsing source. Given a translation unit, this builds a real basic-block
control-flow graph for any `FunctionDecl` in it using the rule-engine's
`CFGEngine`, for use by review/debugging UIs.
"""

from __future__ import annotations

from typing import Any

from misra_platform_rules.analyzers import CFGEngine, ControlFlowGraph
from misra_platform_rules.ast_graph import AstGraph

from misra_platform.core.config import Settings
from misra_platform.domain.models.analysis import TranslationUnitRecord
from misra_platform.integrations.storage.local import LocalArtifactStorage


class TranslationUnitNotFoundError(Exception):
    pass


class AstArtifactUnavailableError(Exception):
    pass


class FunctionNotFoundError(Exception):
    pass


def _has_body(function_node: dict[str, Any], graph: AstGraph) -> bool:
    return any(
        child.get("node_kind") == "CompoundStmt" for child in graph.children(function_node["node_id"])
    )


class CfgService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.storage = LocalArtifactStorage(settings)

    def _load_graph(self, record: TranslationUnitRecord) -> AstGraph:
        if not record.ast_cache_path:
            raise AstArtifactUnavailableError("AST artifact not available for this translation unit")
        payload = self.storage.read_ast_artifact(record.ast_cache_path)
        return AstGraph(payload.get("nodes", []))

    def list_functions(self, record: TranslationUnitRecord) -> list[dict[str, Any]]:
        graph = self._load_graph(record)
        functions = []
        for node in graph.nodes_by_kind("FunctionDecl"):
            properties = node.get("semantic_properties", {}) or {}
            source_range = node.get("source_range", {}) or {}
            functions.append(
                {
                    "function_node_id": node.get("node_id"),
                    "name": properties.get("name", ""),
                    "has_body": _has_body(node, graph),
                    "line_start": source_range.get("line_start"),
                    "line_end": source_range.get("line_end"),
                }
            )
        return functions

    def build_cfg(self, record: TranslationUnitRecord, function_node_id: str) -> ControlFlowGraph:
        graph = self._load_graph(record)
        function_node = graph.get(function_node_id)
        if function_node is None or function_node.get("node_kind") != "FunctionDecl":
            raise FunctionNotFoundError(f"No FunctionDecl node with id {function_node_id!r}")
        if not _has_body(function_node, graph):
            raise FunctionNotFoundError("Function has no body (prototype-only); no CFG to build")
        return CFGEngine().build(function_node, graph)


def get_cfg_service(settings: Settings) -> CfgService:
    return CfgService(settings)
