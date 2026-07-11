import time
from dataclasses import dataclass
from typing import Any

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

from misra_platform.core.config import Settings
from misra_platform.core.logging import get_logger
from misra_platform.integrations.clang_bridge.generated import (
    clang_analysis_pb2,
    clang_analysis_pb2_grpc,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class ParseTranslationUnitResult:
    success: bool
    status_message: str
    translation_unit_id: str
    translation_unit_hash: str
    parse_duration_ms: int
    nodes: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]
    preprocessor: dict[str, Any]


class ClangAstClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._channel = grpc.aio.insecure_channel(settings.clang_worker_address)

    async def check_health(self) -> dict[str, str | float | bool]:
        started = time.perf_counter()
        try:
            stub = health_pb2_grpc.HealthStub(self._channel)
            response = await stub.Check(
                health_pb2.HealthCheckRequest(service=""),
                timeout=self._settings.clang_worker_timeout_seconds,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            is_serving = response.status == health_pb2.HealthCheckResponse.SERVING
            return {
                "status": "up" if is_serving else "down",
                "latency_ms": round(latency_ms, 2),
                "message": "SERVING" if is_serving else "NOT_SERVING",
                "ready": is_serving,
            }
        except grpc.RpcError as error:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.warning("clang_worker_health_failed", error=str(error))
            return {
                "status": "down",
                "latency_ms": round(latency_ms, 2),
                "message": str(error),
                "ready": False,
            }

    async def parse_translation_unit(
        self,
        *,
        file_path: str,
        working_directory: str,
        compile_flags: list[str],
        toolchain_profile_id: str,
        target_triple: str = "",
        include_paths: list[str] | None = None,
        defines: dict[str, str] | None = None,
    ) -> ParseTranslationUnitResult:
        stub = clang_analysis_pb2_grpc.ClangAnalysisServiceStub(self._channel)
        request = clang_analysis_pb2.ParseTranslationUnitRequest(
            file_path=file_path,
            working_directory=working_directory,
            compile_flags=compile_flags,
            toolchain_profile_id=toolchain_profile_id,
            target_triple=target_triple,
            include_paths=include_paths or [],
            ast_schema_version=2,
        )
        if defines:
            for key, value in defines.items():
                request.defines[key] = value

        response = await stub.ParseTranslationUnit(
            request,
            timeout=self._settings.clang_worker_parse_timeout_seconds,
        )

        return ParseTranslationUnitResult(
            success=response.success,
            status_message=response.status_message,
            translation_unit_id=response.translation_unit_id,
            translation_unit_hash=response.translation_unit_hash,
            parse_duration_ms=response.parse_duration_ms,
            nodes=[_node_to_dict(node) for node in response.nodes],
            diagnostics=[_diagnostic_to_dict(item) for item in response.diagnostics],
            preprocessor=_preprocessor_to_dict(response.preprocessor),
        )

    async def close(self) -> None:
        await self._channel.close()


def _range_to_dict(source_range: clang_analysis_pb2.SourceRange) -> dict[str, Any]:
    return {
        "file_path": source_range.file_path,
        "line_start": source_range.line_start,
        "line_end": source_range.line_end,
        "column_start": source_range.column_start,
        "column_end": source_range.column_end,
        "offset_start": source_range.offset_start,
        "offset_end": source_range.offset_end,
    }


def _node_to_dict(node: clang_analysis_pb2.AstNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "node_kind": node.node_kind,
        "source_range": _range_to_dict(node.source_range),
        "parent_id": node.parent_id,
        "children_ids": list(node.children_ids),
        "type_information": {
            "spelling": node.type_information.spelling,
            "canonical_spelling": node.type_information.canonical_spelling,
            "typedef_chain": node.type_information.typedef_chain,
            "fundamental_kind": node.type_information.fundamental_kind,
            "bit_width": node.type_information.bit_width,
            "is_signed": node.type_information.is_signed,
            "is_integer": node.type_information.is_integer,
            "is_floating": node.type_information.is_floating,
            "is_pointer": node.type_information.is_pointer,
            "is_array": node.type_information.is_array,
            "is_record": node.type_information.is_record,
            "is_typedef": node.type_information.is_typedef,
            "pointee_type": node.type_information.pointee_type,
        },
        "qualifiers": list(node.qualifiers),
        "essential_type": node.essential_type,
        "macro_origin": {
            "from_macro": node.macro_origin.from_macro,
            "macro_name": node.macro_origin.macro_name,
            "expansion_chain": list(node.macro_origin.expansion_chain),
        },
        "semantic_properties": dict(node.semantic_properties),
    }


def _diagnostic_to_dict(item: clang_analysis_pb2.DiagnosticMessage) -> dict[str, Any]:
    return {
        "severity": item.severity,
        "message": item.message,
        "category": item.category,
        "range": _range_to_dict(item.range),
    }


def _preprocessor_to_dict(preprocessor: clang_analysis_pb2.PreprocessorMetadata) -> dict[str, Any]:
    return {
        "macro_definitions": [
            {
                "name": item.name,
                "value": item.value,
                "is_function_like": item.is_function_like,
                "file_path": item.file_path,
                "range": _range_to_dict(item.range),
            }
            for item in preprocessor.macro_definitions
        ],
        "macro_expansions": [
            {
                "name": item.name,
                "replacement": item.replacement,
                "chain": list(item.chain),
                "use_range": _range_to_dict(item.use_range),
                "definition_range": _range_to_dict(item.definition_range),
            }
            for item in preprocessor.macro_expansions
        ],
        "include_directives": [
            {
                "included_file": item.included_file,
                "resolved_path": item.resolved_path,
                "is_system": item.is_system,
                "range": _range_to_dict(item.range),
            }
            for item in preprocessor.include_directives
        ],
        "conditional_branches": [
            {
                "condition": item.condition,
                "taken": item.taken,
                "directive": item.directive,
                "range": _range_to_dict(item.range),
            }
            for item in preprocessor.conditional_branches
        ],
    }
