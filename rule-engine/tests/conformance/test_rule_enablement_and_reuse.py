"""Phase 5 deliverables: rule enablement gate + analyzer reuse report.

Generates two machine-readable reports under `rule-engine/reports/` by
actually exercising every registered rule's `detect()` against its
conformance suite:

  * `rule_enablement.json` -- per-rule enabled/experimental/disabled
    decision, derived from conformance completeness (all five case kinds
    present) and confidence calibration (precision/recall/false positive
    rate thresholds).
  * `analyzer_reuse.json` -- per-rule record of which shared analyzers
    (`cfg_v2`, `dataflow_v2`, `aliases`, `essential_types_v2`, ...) were
    actually invoked, used to check the "no rule reimplements shared
    analysis logic" policy is being followed in practice rather than by
    convention.

Both reports are regenerated on every run so they never drift from the
current rule set.
"""

import json
from pathlib import Path

import pytest

from conformance.fixtures import build_all_suites

from misra_platform_rules import analyzer_reuse
from misra_platform_rules.analyzer_efficiency import build_reuse_report
from misra_platform_rules.conformance import ConformanceRunner
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_enablement import enablement_summary, evaluate_all

_REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
_ENABLEMENT_REPORT_PATH = _REPORTS_DIR / "rule_enablement.json"
_REUSE_REPORT_PATH = _REPORTS_DIR / "analyzer_reuse.json"
_PREFLIGHT_REUSE_REPORT_PATH = _REPORTS_DIR / "reuse_report.json"


@pytest.fixture(scope="module")
def suites():
    return build_all_suites()


@pytest.fixture(scope="module")
def plugins():
    registry = create_default_registry()
    return {rule_id: registry.get(rule_id) for rule_id in registry.list_rule_ids()}


def test_rule_enablement_report(suites, plugins) -> None:
    runner = ConformanceRunner()
    suites_by_id = {suite.rule_id: suite for suite in suites}
    metrics_by_id = {}
    for suite in suites:
        plugin = plugins.get(suite.rule_id)
        assert plugin is not None, f"{suite.rule_id} is not registered"
        metrics_by_id[suite.rule_id] = runner.run(plugin, suite)

    # Every registered rule must have a suite at all -- a rule with zero
    # conformance cases is the clearest possible "no tests" violation.
    missing_suite = sorted(set(plugins) - set(suites_by_id))
    for rule_id in missing_suite:
        suites_by_id[rule_id] = None  # type: ignore[assignment]

    decisions = evaluate_all(
        {rid: s for rid, s in suites_by_id.items() if s is not None},
        metrics_by_id,
    )
    decisions_by_id = {d.rule_id: d for d in decisions}
    for rule_id in missing_suite:
        from misra_platform_rules.rule_enablement import REQUIRED_CASE_KINDS, RuleEnablementDecision

        decisions_by_id[rule_id] = RuleEnablementDecision(
            rule_id=rule_id,
            conformance_complete=False,
            missing_case_kinds=sorted(REQUIRED_CASE_KINDS),
            precision=0.0,
            recall=0.0,
            false_positive_rate=1.0,
            total_cases=0,
            enabled_by_default=False,
            experimental=False,
            legacy_partial_conformance=False,
            reason="disabled: no conformance suite registered for this rule",
        )

    all_decisions = list(decisions_by_id.values())
    summary = enablement_summary(all_decisions)
    summary["decisions"] = [d.as_dict() for d in sorted(all_decisions, key=lambda d: d.rule_id)]

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _ENABLEMENT_REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Policy: every registered rule has at least a positive/negative
    # conformance pair, so nothing should land in the hard-disabled bucket.
    # Rules predating the Phase 5 five-kind requirement are grandfathered
    # into `legacy_partial_conformance_rule_ids` (tracked, not disabled);
    # every rule shipped from Phase 5 onward must have the full five kinds.
    assert summary["disabled_count"] == 0, (
        "Rules registered without even minimal conformance coverage: " f"{summary['disabled_rule_ids']}"
    )
    assert summary["legacy_partial_conformance_count"] == 36
    assert summary["experimental_count"] == 36


def test_analyzer_reuse_report(suites, plugins) -> None:
    analyzer_reuse.reset()
    runner = ConformanceRunner()
    for suite in suites:
        plugin = plugins.get(suite.rule_id)
        assert plugin is not None
        runner.run(plugin, suite)

    rule_ids = sorted(plugins.keys())
    summary = analyzer_reuse.reuse_summary(rule_ids)
    preflight_reuse = build_reuse_report(rule_ids)

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _REUSE_REPORT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _PREFLIGHT_REUSE_REPORT_PATH.write_text(json.dumps(preflight_reuse, indent=2), encoding="utf-8")

    # Not every rule needs a *heavy* shared analyzer (some Category A rules
    # are legitimately pure AST-shape matches with no type/CFG/dataflow
    # reasoning at all), so this isn't a hard gate. It's tracked so reuse
    # can be watched over time as new rule packs land.
    assert summary["total_rules"] == len(rule_ids)
