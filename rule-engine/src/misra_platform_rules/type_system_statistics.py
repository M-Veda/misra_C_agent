"""Phase 6.3 deliverable: aggregate type-system statistics from AST artifacts.

Scans conformance (or production) AST payloads and emits four JSON reports
under ``rule-engine/reports/`` for type-conversion coverage analysis.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from misra_platform_rules.analyzers.cast_analyzer import CastAnalyzer
from misra_platform_rules.analyzers.essential_type_analyzer import EssentialTypeAnalyzer
from misra_platform_rules.ast_graph import AstGraph

_REPORT_NAMES = (
    "type_conversion_statistics.json",
    "essential_type_mismatch_statistics.json",
    "enum_conversion_statistics.json",
    "signedness_conversion_statistics.json",
)


def _pair_key(left: str, right: str) -> str:
    return f"{left}->{right}"


def collect_statistics(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    essential_types = EssentialTypeAnalyzer()
    casts = CastAnalyzer(essential_types)

    type_conversions: Counter[str] = Counter()
    essential_mismatches: Counter[str] = Counter()
    enum_conversions: Counter[str] = Counter()
    signedness_conversions: Counter[str] = Counter()

    assignment_count = 0
    cast_count = 0
    binary_op_count = 0

    for artifact in artifacts:
        graph = AstGraph(artifact.get("nodes", []))

        for node in graph.nodes_by_kind("BinaryOperator"):
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            children = graph.children(node["node_id"])
            if len(children) < 2:
                continue
            left_type = essential_types.essential_type_of(children[0])
            right_type = essential_types.essential_type_of(children[1])
            if left_type == "unknown" or right_type == "unknown":
                continue

            if opcode == "=":
                assignment_count += 1
                type_conversions[_pair_key(right_type, left_type)] += 1
                if essential_types.category(left_type) != essential_types.category(right_type):
                    essential_mismatches[_pair_key(left_type, right_type)] += 1
                if essential_types.is_signed(left_type) != essential_types.is_signed(right_type):
                    if essential_types.is_signed(left_type) or essential_types.is_signed(right_type):
                        signedness_conversions[_pair_key(left_type, right_type)] += 1
                if "enum" in left_type or "enum" in right_type:
                    enum_conversions[_pair_key(right_type, left_type)] += 1
            elif opcode in {"+", "-", "*", "/", "%", "<<", ">>", "==", "!=", "<", ">", "<=", ">="}:
                binary_op_count += 1
                if essential_types.category(left_type) != essential_types.category(right_type):
                    essential_mismatches[_pair_key(left_type, right_type)] += 1

        for node in graph.nodes_by_kind("CStyleCastExpr"):
            children = graph.children(node["node_id"])
            if not children:
                continue
            operand = children[0]
            source = essential_types.essential_type_of(operand)
            target = essential_types.essential_type_of(node)
            if source == "unknown" or target == "unknown":
                continue
            cast_count += 1
            type_conversions[_pair_key(source, target)] += 1
            if essential_types.category(source) != essential_types.category(target):
                essential_mismatches[_pair_key(source, target)] += 1
            if casts.is_composite_expression(operand):
                type_conversions["composite_cast"] += 1
            if essential_types.is_signed(source) != essential_types.is_signed(target):
                if essential_types.is_signed(source) or essential_types.is_signed(target):
                    signedness_conversions[_pair_key(source, target)] += 1
            if "enum" in source or "enum" in target:
                enum_conversions[_pair_key(source, target)] += 1

    artifact_count = len(artifacts)
    return {
        "type_conversion_statistics.json": {
            "artifact_count": artifact_count,
            "assignment_count": assignment_count,
            "explicit_cast_count": cast_count,
            "binary_operator_count": binary_op_count,
            "conversion_pairs": dict(type_conversions.most_common()),
            "top_conversion_pairs": type_conversions.most_common(10),
        },
        "essential_type_mismatch_statistics.json": {
            "artifact_count": artifact_count,
            "mismatch_pair_count": sum(essential_mismatches.values()),
            "mismatch_pairs": dict(essential_mismatches.most_common()),
            "top_mismatch_pairs": essential_mismatches.most_common(10),
        },
        "enum_conversion_statistics.json": {
            "artifact_count": artifact_count,
            "enum_conversion_count": sum(enum_conversions.values()),
            "enum_conversion_pairs": dict(enum_conversions.most_common()),
            "top_enum_pairs": enum_conversions.most_common(10),
        },
        "signedness_conversion_statistics.json": {
            "artifact_count": artifact_count,
            "signedness_conversion_count": sum(signedness_conversions.values()),
            "signedness_pairs": dict(signedness_conversions.most_common()),
            "top_signedness_pairs": signedness_conversions.most_common(10),
        },
    }


def write_type_system_reports(
    artifacts: list[dict[str, Any]],
    reports_dir: Path | str,
) -> dict[str, Path]:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    statistics = collect_statistics(artifacts)
    written: dict[str, Path] = {}
    for filename, payload in statistics.items():
        path = reports_dir / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written[filename] = path
    return written
