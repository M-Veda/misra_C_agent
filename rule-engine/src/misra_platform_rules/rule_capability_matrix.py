"""Phase 4 deliverable: rule capability matrix + automatic implementation
roadmap generator.

For every MISRA C:2012 rule in `coverage_matrix.py`, determines which
semantic capabilities it needs (AST-only, type-system, CFG, data-flow,
linkage, alias-analysis) and classifies it into an implementation-readiness
tier by cross-referencing the *reason* previously documented for why it
wasn't built yet against the shared analysis infrastructure that exists as
of Phase 4 (every capability dimension below now has at least one real
analyzer — `CFGEngine`, `DataFlowEngineV2`, `AliasAnalyzer`,
`EssentialTypeEngine`, `LinkageAnalyzer` — see `analyzers/`).

This is intentionally rule-based (not hand-maintained per rule): the tier
comes from re-classifying the existing `unsupported_reason` text, so as
Phase 3's per-rule notes are updated, this regenerates automatically rather
than needing a parallel hand-kept roadmap document.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from misra_platform_rules.coverage_matrix import (
    CoverageEntry,
    build_coverage_matrix,
    mark_implemented,
)
from misra_platform_rules.taxonomy import RuleImplementationCategory as Cat

# Rules whose correct implementation fundamentally needs points-to/aliasing
# reasoning (does pointer A refer to the same storage as B / array C /
# object D?) on top of whatever their nominal `Cat` category already
# implies. Not derivable from `Cat` alone since aliasing cuts across the
# A-G taxonomy (e.g. 19.1 is nominally data-flow, but the data flow in
# question is specifically about overlapping storage).
_ALIAS_ANALYSIS_RULES = {
    "18.1",  # pointer arithmetic within array bounds
    "18.3",  # relational operators on pointers into the same object
    "19.1",  # assignment/copy to an overlapping object
    "21.15",  # memcpy/memmove/memcmp pointer-compatibility
    "21.17",  # string function buffer overflow/underflow
    "21.18",  # size_t argument vs destination object size
    "21.20",  # pointer used after a subsequent invalidating call
    "22.6",  # FILE* used after the stream is closed
}

# Substrings (lowercased) of a documented `unsupported_reason` that mean
# "blocked on a new raw-AST field clang-worker doesn't serialize yet" — an
# AST-schema/toolchain change, not a missing *analyzer*. Every analyzer
# capability this module tracks (ast/type/cfg/dataflow/linkage/alias) has
# at least one real implementation as of Phase 4; these markers catch the
# remaining "we don't have the raw data at all" blockers.
_AST_METADATA_GAP_MARKERS = (
    "raw literal spelling",
    "raw token",
    "raw source text",
    "raw macro-body",
    "bit-field metadata",
    "bit-field width metadata",
    "array-size expression",
    "array-size-expression",
    "enumerator value metadata",
    "incomplete-type metadata",
    "nested-pointer-depth metadata",
    "designated-initializer metadata",
    "initializer-list bracket metadata",
    "implicit-parenthesization metadata",
    "call-site argument shape metadata",
    "call-argument value-range",
    "parameter-decay metadata",
    "namespace tagging",
    "#undef event tracking",
    "fopen mode string tracking",
    "extension list",
    "language-standard-version",
)

# Substrings meaning "this is a process/documentation/toolchain concern,
# not something an AST-level analyzer can ever mechanically decide" —
# permanently out of scope for automated detection, not a roadmap item.
_PROCESS_CONCERN_MARKERS = (
    "process/toolchain",
    "process concern",
    "requirements traceability",
    "design-level directive",
    "not code-analyzable",
    "compiler-diagnostics-level",
)


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    ast_only: bool
    type_system: bool
    cfg: bool
    dataflow: bool
    linkage: bool
    alias_analysis: bool

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RoadmapEntry:
    identifier: str
    title: str
    misra_class: str
    capabilities: CapabilityRequirement
    tier: str  # implemented | ready_now | blocked_on_ast_metadata | blocked_on_process
    reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "title": self.title,
            "misra_class": self.misra_class,
            "capabilities": self.capabilities.as_dict(),
            "tier": self.tier,
            "reason": self.reason,
        }


_CATEGORY_CAPABILITIES: dict[Cat, CapabilityRequirement] = {
    Cat.A_AST_ONLY: CapabilityRequirement(True, False, False, False, False, False),
    Cat.B_TYPE_SYSTEM: CapabilityRequirement(True, True, False, False, False, False),
    Cat.C_CONTROL_FLOW: CapabilityRequirement(True, False, True, False, False, False),
    Cat.D_DATA_FLOW: CapabilityRequirement(True, False, True, True, False, False),
    Cat.E_CROSS_TRANSLATION_UNIT: CapabilityRequirement(True, False, False, False, True, False),
    Cat.F_PREPROCESSOR: CapabilityRequirement(True, False, False, False, False, False),
    Cat.G_CONFIGURATION_BUILD: CapabilityRequirement(False, False, False, False, False, False),
}

_DEFAULT_CAPABILITIES = CapabilityRequirement(True, False, False, False, False, False)


def capabilities_for(entry: CoverageEntry) -> CapabilityRequirement:
    base = _CATEGORY_CAPABILITIES.get(entry.category, _DEFAULT_CAPABILITIES)
    if entry.identifier in _ALIAS_ANALYSIS_RULES:
        return CapabilityRequirement(
            ast_only=base.ast_only,
            type_system=base.type_system,
            cfg=base.cfg,
            dataflow=True,
            linkage=base.linkage,
            alias_analysis=True,
        )
    return base


def _classify_tier(entry: CoverageEntry) -> str:
    if entry.implemented_rule_id:
        return "implemented"
    reason = (entry.unsupported_reason or "").lower()
    if entry.category == Cat.G_CONFIGURATION_BUILD or any(
        marker in reason for marker in _PROCESS_CONCERN_MARKERS
    ):
        return "blocked_on_process"
    if any(marker in reason for marker in _AST_METADATA_GAP_MARKERS):
        return "blocked_on_ast_metadata"
    return "ready_now"


def build_roadmap(registered_rule_ids: set[str] | None = None) -> list[RoadmapEntry]:
    entries = build_coverage_matrix()
    if registered_rule_ids is not None:
        entries = mark_implemented(entries, registered_rule_ids)

    roadmap: list[RoadmapEntry] = []
    for entry in entries:
        if entry.kind != "rule":
            continue
        roadmap.append(
            RoadmapEntry(
                identifier=entry.identifier,
                title=entry.title,
                misra_class=entry.misra_class,
                capabilities=capabilities_for(entry),
                tier=_classify_tier(entry),
                reason=entry.unsupported_reason,
            )
        )
    return roadmap


def roadmap_summary(roadmap: list[RoadmapEntry]) -> dict[str, int]:
    counts: dict[str, int] = {"total": len(roadmap)}
    for entry in roadmap:
        counts[entry.tier] = counts.get(entry.tier, 0) + 1
    capability_counts = {
        "ast_only": 0, "type_system": 0, "cfg": 0, "dataflow": 0, "linkage": 0, "alias_analysis": 0,
    }
    for entry in roadmap:
        for key, value in entry.capabilities.as_dict().items():
            if value:
                capability_counts[key] += 1
    return {**counts, **{f"needs_{key}": value for key, value in capability_counts.items()}}
