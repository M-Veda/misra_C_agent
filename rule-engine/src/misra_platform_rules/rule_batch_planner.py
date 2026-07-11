"""Phase 6: automatic rule implementation batch generation from the roadmap.

Consumes `rule_capability_matrix.build_roadmap()` and groups unimplemented
rules into prioritized batches:

  1. `ready_now`        — all required analyzers exist today
  2. `blocked_on_ast_metadata` — needs a new clang-worker AST field
  3. `blocked_on_process` — permanently outside mechanical analysis

Within each tier, rules are further grouped by their dominant capability
requirement (AST-only, type-system, CFG, dataflow, linkage, alias) so
implementers can land one analyzer-reuse pattern at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from misra_platform_rules.rule_capability_matrix import (
    CapabilityRequirement,
    RoadmapEntry,
    build_roadmap,
)

_TIER_ORDER = ("ready_now", "blocked_on_ast_metadata", "blocked_on_process")

_CAPABILITY_KEYS = (
    "type_system",
    "cfg",
    "dataflow",
    "linkage",
    "alias_analysis",
)


@dataclass(frozen=True, slots=True)
class RuleBatch:
    tier: str
    capability_group: str
    rule_ids: list[str]
    identifiers: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "capability_group": self.capability_group,
            "rule_count": len(self.rule_ids),
            "rule_ids": self.rule_ids,
            "identifiers": self.identifiers,
        }


def _dominant_capability(cap: CapabilityRequirement) -> str:
    """Pick the 'heaviest' capability a rule needs for batch grouping."""
    if cap.alias_analysis:
        return "alias_analysis"
    if cap.dataflow:
        return "dataflow"
    if cap.cfg:
        return "cfg"
    if cap.linkage:
        return "linkage"
    if cap.type_system:
        return "type_system"
    return "ast_only"


def _rule_id(identifier: str) -> str:
    return f"misra-c2012-rule-{identifier.replace('.', '-')}"


def generate_batches(registered_rule_ids: set[str] | None = None) -> list[RuleBatch]:
    roadmap = build_roadmap(registered_rule_ids)
    pending = [entry for entry in roadmap if entry.tier != "implemented"]

    batches: list[RuleBatch] = []
    for tier in _TIER_ORDER:
        tier_entries = [e for e in pending if e.tier == tier]
        by_group: dict[str, list[RoadmapEntry]] = {}
        for entry in tier_entries:
            group = _dominant_capability(entry.capabilities)
            by_group.setdefault(group, []).append(entry)

        for group in sorted(by_group.keys()):
            entries = sorted(by_group[group], key=lambda e: e.identifier)
            batches.append(
                RuleBatch(
                    tier=tier,
                    capability_group=group,
                    rule_ids=[_rule_id(e.identifier) for e in entries],
                    identifiers=[e.identifier for e in entries],
                )
            )
    return batches


def batch_summary(batches: list[RuleBatch]) -> dict[str, Any]:
    by_tier: dict[str, int] = {}
    by_group: dict[str, int] = {}
    for batch in batches:
        by_tier[batch.tier] = by_tier.get(batch.tier, 0) + len(batch.rule_ids)
        key = f"{batch.tier}/{batch.capability_group}"
        by_group[key] = len(batch.rule_ids)
    return {
        "total_pending": sum(len(b.rule_ids) for b in batches),
        "batch_count": len(batches),
        "by_tier": by_tier,
        "by_tier_and_capability": by_group,
        "batches": [b.as_dict() for b in batches],
    }
