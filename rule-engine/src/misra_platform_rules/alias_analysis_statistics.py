"""Phase 6.5 deliverable: aggregate alias-analysis statistics from AST artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from misra_platform_rules.analyzers.alias_analyzer import AliasAnalyzer
from misra_platform_rules.ast_graph import AstGraph

_REPORT_NAMES = (
    "alias_analysis_statistics.json",
    "unsupported_alias_patterns.json",
)


def collect_statistics(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    alias_pairs: Counter[str] = Counter()
    violation_counts: Counter[str] = Counter()
    unsupported: Counter[str] = Counter()
    function_count = 0
    pointer_count = 0

    for artifact in artifacts:
        graph = AstGraph(artifact.get("nodes", []))
        for function_node in graph.nodes_by_kind("FunctionDecl"):
            if not any(
                child.get("node_kind") == "CompoundStmt"
                for child in graph.children(function_node["node_id"])
            ):
                continue
            function_count += 1
            aliases = AliasAnalyzer().analyze(function_node, graph)
            pointer_count += len(aliases.all_pointer_names())

            for left in aliases.all_pointer_names():
                for right in aliases.all_pointer_names():
                    if left >= right:
                        continue
                    may_alias, confidence = aliases.may_alias(left, right)
                    if may_alias:
                        alias_pairs[f"{left}<->{right} ({confidence})"] += 1

            violation_counts["pointer_arithmetic"] += len(
                aliases.pointer_arithmetic_violations(function_node, graph)
            )
            violation_counts["incompatible_mem"] += len(
                aliases.incompatible_mem_calls(function_node, graph)
            )
            violation_counts["string_overflow"] += len(
                aliases.string_buffer_overflow_calls(function_node, graph)
            )
            violation_counts["size_exceeds_destination"] += len(
                aliases.size_exceeds_destination_calls(function_node, graph)
            )
            violation_counts["use_after_string_invalidation"] += len(
                aliases.use_after_string_invalidation_reads(function_node, graph)
            )
            violation_counts["use_after_file_close"] += len(
                aliases.use_after_file_close_reads(function_node, graph)
            )

            for pattern in aliases.unsupported_patterns(function_node, graph):
                unsupported[pattern] += 1

    artifact_count = len(artifacts)
    return {
        "alias_analysis_statistics.json": {
            "artifact_count": artifact_count,
            "function_count": function_count,
            "pointer_variable_count": pointer_count,
            "may_alias_pair_count": sum(alias_pairs.values()),
            "alias_pairs": dict(alias_pairs.most_common()),
            "top_alias_pairs": alias_pairs.most_common(10),
            "violation_signals": dict(violation_counts),
            "total_violation_signals": sum(violation_counts.values()),
        },
        "unsupported_alias_patterns.json": {
            "artifact_count": artifact_count,
            "function_count": function_count,
            "unsupported_pattern_count": sum(unsupported.values()),
            "patterns": dict(unsupported.most_common()),
            "top_patterns": unsupported.most_common(10),
            "documented_limitations": [
                "heap_allocation_opaque_target: malloc/calloc/realloc targets are unknown",
                "pointer_arithmetic_unknown_pointee: pointer arithmetic on unknown-origin pointers",
                "parameter_pointer_unknown_target: pointer parameters seeded as unknown",
                "flow_insensitive_points_to: may-alias is whole-function, not per program point",
                "no_interprocedural_alias: callee effects on pointer arguments are not summarized",
            ],
        },
    }


def write_alias_analysis_reports(
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
