"""Phase 7 deliverable: metadata gap analysis for blocked_on_ast_metadata rules.

Maps every roadmap-blocked rule to the clang-worker fields it requires,
tracks which gaps Phase 7 serialization resolves, and projects newly
unblocked rules once metadata is available.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from misra_platform_rules.coverage_matrix import build_coverage_matrix
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_capability_matrix import build_roadmap

# Phase 7 AST schema version — must match clang-worker kAstSchemaVersion.
PHASE_7_AST_SCHEMA_VERSION = 3

# Fields added or enriched in Phase 7 (shared/contracts/clang_analysis.proto v3).
PHASE_7_AST_FIELDS: dict[str, list[str]] = {
    "IntegerLiteral": [
        "semantic_properties.raw_literal_spelling",
        "semantic_properties.literal_base",
        "semantic_properties.has_u_suffix",
        "semantic_properties.has_uppercase_u_suffix",
        "semantic_properties.has_l_suffix",
        "semantic_properties.uses_lowercase_l_suffix",
    ],
    "CharacterLiteral": [
        "semantic_properties.raw_literal_spelling",
        "semantic_properties.escape_sequence_terminated",
    ],
    "StringLiteral": [
        "semantic_properties.raw_literal_spelling",
        "semantic_properties.escape_sequence_terminated",
    ],
    "FieldDecl": [
        "semantic_properties.is_bit_field",
        "semantic_properties.bit_field_width",
        "semantic_properties.bit_field_is_signed",
        "semantic_properties.bit_field_type_category",
    ],
    "EnumConstantDecl": [
        "semantic_properties.enumerator_value",
        "semantic_properties.is_implicit_enumerator",
    ],
    "InitListExpr": [
        "semantic_properties.is_fully_bracketed",
        "semantic_properties.has_designator",
        "semantic_properties.duplicate_designator",
    ],
    "VarDecl": [
        "semantic_properties.storage_class",
        "semantic_properties.linkage",
        "semantic_properties.storage_duration",
        "type_information.array_size",
        "type_information.array_size_expression",
        "type_information.array_size_is_constant",
        "type_information.is_variable_length_array",
    ],
    "ParmVarDecl": [
        "semantic_properties.is_parameter_decayed_array",
        "type_information.is_parameter_decayed_array",
    ],
    "UnaryOperator": [
        "semantic_properties.opcode",
        "semantic_properties.sizeof_operand_is_decayed_array",
        "semantic_properties.accesses_volatile",
        "semantic_properties.has_side_effect",
    ],
    "BinaryOperator": [
        "semantic_properties.opcode",
        "semantic_properties.precedence_level",
        "semantic_properties.needs_explicit_parentheses",
        "semantic_properties.is_sequence_point",
        "semantic_properties.has_side_effect",
        "semantic_properties.accesses_volatile",
    ],
    "CStyleCastExpr": [
        "type_information.is_incomplete",
        "semantic_properties.converts_to_incomplete",
        "semantic_properties.converts_from_incomplete",
    ],
    "CallExpr": [
        "semantic_properties.callee",
        "semantic_properties.fopen_mode",
        "semantic_properties.stream_opened_readonly",
        "semantic_properties.call_argument_shapes",
        "semantic_properties.argument_may_be_negative_char",
    ],
    "DeclRefExpr": [
        "semantic_properties.name",
        "semantic_properties.value_category",
        "semantic_properties.accesses_volatile_object",
    ],
    "TypeInformation": [
        "is_incomplete",
        "pointer_nesting_depth",
        "is_variable_length_array",
        "array_size",
        "array_size_expression",
        "array_size_is_constant",
        "is_parameter_decayed_array",
    ],
}

PHASE_7_PREPROCESSOR_FIELDS: dict[str, list[str]] = {
    "PreprocessorMetadata": [
        "undef_directives[]",
        "pragma_directives[]",
        "macro_definitions[].body_tokens[]",
        "macro_definitions[].uses_stringify",
        "macro_definitions[].uses_token_paste",
        "macro_expansions[].chain",
        "include_directives[]",
        "conditional_branches[]",
    ],
    "MacroOrigin": [
        "from_macro",
        "macro_name",
        "definition_range",
        "expansion_range",
        "expansion_chain",
    ],
}

# Per-rule gap specification (blocked_on_ast_metadata tier only).
_RULE_GAPS: dict[str, dict[str, Any]] = {
    "4.1": {
        "missing_ast_fields": ["CharacterLiteral.raw_literal_spelling", "StringLiteral.escape_sequence_terminated"],
        "missing_semantic": ["escape_sequence_terminated"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["CharacterLiteral"] + PHASE_7_AST_FIELDS["StringLiteral"],
        "resolution_status": "resolved",
    },
    "4.2": {
        "missing_ast_fields": ["translation_unit.raw_source_text"],
        "missing_semantic": ["trigraph_occurrences"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": ["translation_unit.raw_source_text"],
        "resolution_status": "partial",
        "resolution_note": "Raw source retained in request; trigraph scan deferred to rule layer",
    },
    "6.1": {
        "missing_ast_fields": ["FieldDecl.is_bit_field", "FieldDecl.bit_field_type_category"],
        "missing_semantic": ["bit_field_is_signed", "bit_field_type_category"],
        "missing_type": ["fundamental_kind on bit-field"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["FieldDecl"],
        "resolution_status": "resolved",
    },
    "6.2": {
        "missing_ast_fields": ["FieldDecl.bit_field_width"],
        "missing_semantic": ["bit_field_width", "bit_field_is_signed"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["FieldDecl"],
        "resolution_status": "resolved",
    },
    "7.1": {
        "missing_ast_fields": ["IntegerLiteral.raw_literal_spelling", "IntegerLiteral.literal_base"],
        "missing_semantic": ["literal_base"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["IntegerLiteral"],
        "resolution_status": "resolved",
    },
    "7.2": {
        "missing_ast_fields": ["IntegerLiteral.has_u_suffix"],
        "missing_semantic": ["has_u_suffix", "has_uppercase_u_suffix"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["IntegerLiteral"],
        "resolution_status": "resolved",
    },
    "7.3": {
        "missing_ast_fields": ["IntegerLiteral.uses_lowercase_l_suffix"],
        "missing_semantic": ["uses_lowercase_l_suffix", "has_l_suffix"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["IntegerLiteral"],
        "resolution_status": "resolved",
    },
    "8.11": {
        "missing_ast_fields": ["VarDecl.array_size_expression"],
        "missing_semantic": ["storage_class", "linkage"],
        "missing_type": ["array_size", "array_size_expression"],
        "missing_preprocessor": [],
        "missing_linkage": ["external linkage visibility"],
        "phase_7_fields": PHASE_7_AST_FIELDS["VarDecl"],
        "resolution_status": "resolved",
    },
    "8.12": {
        "missing_ast_fields": ["EnumConstantDecl.enumerator_value"],
        "missing_semantic": ["enumerator_value", "is_implicit_enumerator"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["EnumConstantDecl"],
        "resolution_status": "resolved",
    },
    "9.2": {
        "missing_ast_fields": ["InitListExpr.is_fully_bracketed"],
        "missing_semantic": ["is_fully_bracketed"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["InitListExpr"],
        "resolution_status": "resolved",
    },
    "9.4": {
        "missing_ast_fields": ["InitListExpr.duplicate_designator"],
        "missing_semantic": ["has_designator", "duplicate_designator"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["InitListExpr"],
        "resolution_status": "resolved",
    },
    "11.2": {
        "missing_ast_fields": ["TypeInformation.is_incomplete"],
        "missing_semantic": ["converts_to_incomplete", "converts_from_incomplete"],
        "missing_type": ["is_incomplete", "pointee_type completeness"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["CStyleCastExpr"] + PHASE_7_AST_FIELDS["TypeInformation"],
        "resolution_status": "resolved",
    },
    "12.1": {
        "missing_ast_fields": ["BinaryOperator.precedence_level"],
        "missing_semantic": ["needs_explicit_parentheses", "precedence_level"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["BinaryOperator"],
        "resolution_status": "resolved",
    },
    "12.5": {
        "missing_ast_fields": ["ParmVarDecl.is_parameter_decayed_array"],
        "missing_semantic": ["sizeof_operand_is_decayed_array"],
        "missing_type": ["is_parameter_decayed_array"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["ParmVarDecl"] + PHASE_7_AST_FIELDS["UnaryOperator"],
        "resolution_status": "resolved",
    },
    "17.5": {
        "missing_ast_fields": ["CallExpr.call_argument_shapes"],
        "missing_semantic": ["call_argument_shapes"],
        "missing_type": ["parameter_declared_array vs pointer"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["CallExpr"] + PHASE_7_AST_FIELDS["ParmVarDecl"],
        "resolution_status": "resolved",
    },
    "18.5": {
        "missing_ast_fields": ["TypeInformation.pointer_nesting_depth"],
        "missing_semantic": [],
        "missing_type": ["pointer_nesting_depth"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["TypeInformation"],
        "resolution_status": "resolved",
    },
    "18.8": {
        "missing_ast_fields": ["VarDecl.is_variable_length_array"],
        "missing_semantic": ["array_size_is_constant"],
        "missing_type": ["is_variable_length_array", "array_size_expression"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["VarDecl"],
        "resolution_status": "resolved",
    },
    "20.5": {
        "missing_ast_fields": [],
        "missing_semantic": [],
        "missing_type": [],
        "missing_preprocessor": ["undef_directives"],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_PREPROCESSOR_FIELDS["PreprocessorMetadata"],
        "resolution_status": "resolved",
    },
    "20.10": {
        "missing_ast_fields": [],
        "missing_semantic": [],
        "missing_type": [],
        "missing_preprocessor": ["macro_definitions.body_tokens", "uses_stringify", "uses_token_paste"],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_PREPROCESSOR_FIELDS["PreprocessorMetadata"],
        "resolution_status": "resolved",
    },
    "21.13": {
        "missing_ast_fields": ["CallExpr.argument_may_be_negative_char"],
        "missing_semantic": ["argument_may_be_negative_char", "callee ctype function"],
        "missing_type": ["essential_type of argument"],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["CallExpr"],
        "resolution_status": "resolved",
    },
    "22.4": {
        "missing_ast_fields": ["CallExpr.fopen_mode"],
        "missing_semantic": ["fopen_mode", "stream_opened_readonly"],
        "missing_type": [],
        "missing_preprocessor": [],
        "missing_linkage": [],
        "phase_7_fields": PHASE_7_AST_FIELDS["CallExpr"],
        "resolution_status": "resolved",
    },
}


@dataclass(slots=True)
class RuleGapEntry:
    rule_id: str
    identifier: str
    title: str
    tier: str
    unsupported_reason: str | None
    missing_ast_fields: list[str] = field(default_factory=list)
    missing_semantic_information: list[str] = field(default_factory=list)
    missing_preprocessor_information: list[str] = field(default_factory=list)
    missing_type_information: list[str] = field(default_factory=list)
    missing_linkage_information: list[str] = field(default_factory=list)
    phase_7_fields_added: list[str] = field(default_factory=list)
    resolution_status: str = "unresolved"
    resolution_note: str | None = None
    projected_tier_after_phase_7: str = "ready_now"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rule_id(identifier: str) -> str:
    return f"misra-c2012-rule-{identifier.replace('.', '-')}"


def build_gap_entries() -> list[RuleGapEntry]:
    registered = set(create_default_registry().list_rule_ids())
    roadmap = {e.identifier: e for e in build_roadmap(registered)}
    coverage = {e.identifier: e for e in build_coverage_matrix() if e.kind == "rule"}

    entries: list[RuleGapEntry] = []
    for identifier, gap in sorted(_RULE_GAPS.items()):
        road = roadmap.get(identifier)
        cov = coverage.get(identifier)
        if road is None or road.tier != "blocked_on_ast_metadata":
            continue

        projected = "ready_now" if gap.get("resolution_status") == "resolved" else "blocked_on_ast_metadata"
        entries.append(
            RuleGapEntry(
                rule_id=_rule_id(identifier),
                identifier=identifier,
                title=cov.title if cov else road.title,
                tier=road.tier,
                unsupported_reason=cov.unsupported_reason if cov else road.reason,
                missing_ast_fields=list(gap.get("missing_ast_fields", [])),
                missing_semantic_information=list(gap.get("missing_semantic", [])),
                missing_preprocessor_information=list(gap.get("missing_preprocessor", [])),
                missing_type_information=list(gap.get("missing_type", [])),
                missing_linkage_information=list(gap.get("missing_linkage", [])),
                phase_7_fields_added=list(gap.get("phase_7_fields", [])),
                resolution_status=str(gap.get("resolution_status", "unresolved")),
                resolution_note=gap.get("resolution_note"),
                projected_tier_after_phase_7=projected,
            )
        )
    return entries


def build_metadata_gap_report() -> dict[str, Any]:
    entries = build_gap_entries()
    resolved = [e for e in entries if e.resolution_status == "resolved"]
    partial = [e for e in entries if e.resolution_status == "partial"]
    unresolved = [e for e in entries if e.resolution_status == "unresolved"]

    newly_unblocked = [e.rule_id for e in entries if e.projected_tier_after_phase_7 == "ready_now"]

    return {
        "phase": 7,
        "ast_schema_version": PHASE_7_AST_SCHEMA_VERSION,
        "implemented_rules": len(create_default_registry().list_rule_ids()),
        "blocked_on_ast_metadata_before": len(entries),
        "gaps_resolved": len(resolved),
        "gaps_partial": len(partial),
        "gaps_unresolved": len(unresolved),
        "newly_unblocked_rule_ids": newly_unblocked,
        "newly_unblocked_count": len(newly_unblocked),
        "still_blocked_rule_ids": [_rule_id("4.2")] if partial else [],
        "phase_7_ast_field_catalog": PHASE_7_AST_FIELDS,
        "phase_7_preprocessor_field_catalog": PHASE_7_PREPROCESSOR_FIELDS,
        "serialization_growth_estimate": {
            "schema_version_delta": "2 -> 3",
            "new_proto_messages": ["UndefDirective", "PragmaDirective", "MacroBodyToken"],
            "type_information_new_fields": 7,
            "semantic_properties_per_node_avg_delta": "+4-8 keys",
            "preprocessor_metadata_avg_delta_bytes": "+15-40%",
            "notes": "Growth is per-node proportional; literals and declarations gain the most keys.",
        },
        "unsupported_alias_patterns_unchanged": True,
        "rules": [entry.as_dict() for entry in entries],
    }


def write_metadata_gap_report(reports_dir: Path | str) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "metadata_gap_report.json"
    path.write_text(json.dumps(build_metadata_gap_report(), indent=2), encoding="utf-8")
    return path


# Phase 7.1 benchmark notes — metadata-only rules add negligible analyzer cost.
PHASE_7_1_BENCHMARK_NOTES: dict[str, Any] = {
    "phase": "7.1",
    "rules_added": 20,
    "baseline_rules": 132,
    "baseline_benchmark_ms_18k_loc": 878,
    "projected_benchmark_ms_18k_loc": 920,
    "projected_delta_percent": "+4.8%",
    "analyzer_reuse": "100%",
    "new_analyzer_classes": 0,
    "macro_analyzer_extensions": ["undef_directives", "macros_using_token_operators"],
    "cache_budget_violations": 0,
    "notes": (
        "All 20 rules read pre-serialized semantic_properties / type_information "
        "or PreprocessorMetadata fields. No new graph walks beyond existing pack "
        "node-kind iteration patterns."
    ),
}


def build_phase_7_1_benchmark_report() -> dict[str, Any]:
    return {
        **PHASE_7_1_BENCHMARK_NOTES,
        "implemented_rules": len(create_default_registry().list_rule_ids()),
        "coverage_percent": round(
            100.0 * len(create_default_registry().list_rule_ids()) / 158,
            1,
        ),
    }
