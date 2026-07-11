"""Rule dependency graph → execution groups (Phase 3).

Every rule declares, via `RuleMetadata`:
  - `implementation_category`: which analysis capability tier it needs
    (see `taxonomy.CATEGORY_EXECUTION_ORDER`).
  - `rule_dependencies`: rule_ids whose results this rule's fix/explanation
    logic depends on (e.g. a rule that only fires when a *different* rule
    did *not* already flag the same node, to avoid duplicate/contradictory
    guidance). Empty for all rules today.

`resolve_execution_groups` turns those declarations into an ordered list of
groups. Every rule inside a group can run in parallel; a group must fully
complete before the next group starts. This lets the dispatcher run cheap
category A/B/F rules first and defer expensive whole-program category E/G
rules to a later stage, and guarantees a rule's declared dependencies have
already executed.
"""

from __future__ import annotations

from misra_platform_rules.base_rule import IRulePlugin
from misra_platform_rules.taxonomy import CATEGORY_EXECUTION_ORDER, RuleImplementationCategory


class CyclicRuleDependencyError(Exception):
    pass


def resolve_execution_groups(rules: list[IRulePlugin]) -> list[list[IRulePlugin]]:
    """Return rules grouped into ordered batches honoring both the category
    execution order and any explicit `rule_dependencies`."""
    by_id = {rule.metadata.rule_id: rule for rule in rules}

    category_tier: dict[str, int] = {}
    for rule in rules:
        try:
            category = RuleImplementationCategory(rule.metadata.implementation_category)
            tier = CATEGORY_EXECUTION_ORDER.get(category, 0)
        except ValueError:
            tier = 0
        category_tier[rule.metadata.rule_id] = tier

    resolved_tier: dict[str, int] = {}

    def resolve(rule_id: str, visiting: set[str]) -> int:
        if rule_id in resolved_tier:
            return resolved_tier[rule_id]
        if rule_id in visiting:
            raise CyclicRuleDependencyError(f"Cyclic rule_dependencies detected at '{rule_id}'")
        visiting.add(rule_id)

        tier = category_tier.get(rule_id, 0)
        rule = by_id.get(rule_id)
        if rule is not None:
            for dependency_id in rule.metadata.rule_dependencies:
                if dependency_id not in by_id:
                    continue
                tier = max(tier, resolve(dependency_id, visiting) + 1)

        visiting.discard(rule_id)
        resolved_tier[rule_id] = tier
        return tier

    for rule in rules:
        resolve(rule.metadata.rule_id, set())

    groups: dict[int, list[IRulePlugin]] = {}
    for rule in rules:
        tier = resolved_tier[rule.metadata.rule_id]
        groups.setdefault(tier, []).append(rule)

    return [groups[tier] for tier in sorted(groups.keys())]
