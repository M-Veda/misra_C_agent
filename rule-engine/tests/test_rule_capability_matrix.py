from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_capability_matrix import (
    build_roadmap,
    capabilities_for,
    roadmap_summary,
)
from misra_platform_rules.coverage_matrix import build_coverage_matrix


def _registered_ids() -> set[str]:
    registry = create_default_registry()
    return set(registry.list_rule_ids())


def test_roadmap_covers_every_rule_exactly_once():
    coverage = build_coverage_matrix()
    total_rules = sum(1 for e in coverage if e.kind == "rule")
    roadmap = build_roadmap(_registered_ids())
    assert len(roadmap) == total_rules
    assert len({entry.identifier for entry in roadmap}) == total_rules


def test_implemented_rules_are_tiered_implemented():
    roadmap = build_roadmap(_registered_ids())
    by_id = {entry.identifier: entry for entry in roadmap}
    assert by_id["2.1"].tier == "implemented"
    assert by_id["9.1"].tier == "implemented"
    assert by_id["10.1"].tier == "implemented"
    assert by_id["5.2"].tier == "implemented"
    assert by_id["19.1"].tier == "implemented"


def test_process_only_directives_are_blocked_on_process():
    roadmap = build_roadmap(_registered_ids())
    by_id = {entry.identifier: entry for entry in roadmap}
    assert by_id["1.1"].tier == "blocked_on_process"
    entry_capabilities = by_id["1.1"].capabilities
    assert not entry_capabilities.ast_only


def test_raw_ast_metadata_gaps_are_tiered_correctly():
    roadmap = build_roadmap(_registered_ids())
    by_id = {entry.identifier: entry for entry in roadmap}
    assert by_id["4.2"].tier == "blocked_on_ast_metadata"  # trigraphs need raw source scan
    assert by_id["7.1"].tier == "implemented"
    assert by_id["6.1"].tier == "implemented"


def test_reuse_existing_analyzer_rules_are_ready_now():
    roadmap = build_roadmap(_registered_ids())
    by_id = {entry.identifier: entry for entry in roadmap}
    # Phase 6.5 shipped the alias_analysis ready_now batch.
    assert by_id["2.6"].tier == "implemented"
    assert by_id["16.1"].tier == "implemented"
    assert by_id["18.1"].tier == "implemented"
    assert by_id["22.6"].tier == "implemented"
    assert by_id["20.5"].tier == "implemented"


def test_alias_analysis_rules_flagged_correctly():
    coverage = {e.identifier: e for e in build_coverage_matrix()}
    caps = capabilities_for(coverage["19.1"])
    assert caps.alias_analysis is True
    assert caps.dataflow is True

    caps_ast_only = capabilities_for(coverage["8.2"])
    assert caps_ast_only.alias_analysis is False
    assert caps_ast_only.ast_only is True


def test_roadmap_summary_counts_are_consistent():
    roadmap = build_roadmap(_registered_ids())
    summary = roadmap_summary(roadmap)
    assert summary["total"] == len(roadmap)
    tiers = {"implemented", "ready_now", "blocked_on_ast_metadata", "blocked_on_process"}
    assert sum(summary.get(tier, 0) for tier in tiers) == summary["total"]
    assert summary["needs_cfg"] >= 1
    assert summary["needs_alias_analysis"] == len(
        [e for e in roadmap if e.capabilities.alias_analysis]
    )


def test_without_registry_crosscheck_reason_none_counts_as_implemented_candidate():
    # Without a live registry, any rule whose documented reason is None is
    # treated as "should already be implemented" per coverage_matrix rules.
    roadmap = build_roadmap(registered_rule_ids=None)
    by_id = {entry.identifier: entry for entry in roadmap}
    assert by_id["2.1"].tier == "implemented"
