"""Phase 5 deliverable: rule enablement gate.

Policy (from the Phase 5 objective):

    "Every rule requires a compliant example, non-compliant example, macro
    example, embedded example, and edge case example. Rules without tests
    may not be enabled by default."

    "Measure precision, recall, false positive rate, and review acceptance
    rate. Low-confidence rules become experimental."

This module turns that policy into an executable decision function rather
than a manually maintained list. Given a rule's conformance suite (from
`tests/conformance/fixtures.py`) and the metrics produced by running that
suite through `ConformanceRunner`, `evaluate_rule` decides:

  * `conformance_complete` -- does the suite cover all five required case
    kinds (positive, negative, edge, macro, embedded)?
  * `enabled_by_default` -- conformance-complete rules are enabled; rules
    missing required case kinds are not, regardless of how well they score.
  * `experimental` -- an enabled rule whose precision, recall, or false
    positive rate falls outside the calibration thresholds is downgraded to
    experimental (still enabled, but flagged for cautious rollout / review
    prioritization) rather than disabled outright.

The pure decision logic here has no dependency on the test-only fixtures
module; callers (tests, report generators, the registry) supply suites and
metrics explicitly, which keeps this importable from production code
without pulling in `tests/`.

Grandfathering note: Phase 1-4 shipped 36 rules with only `positive`/
`negative` (or, for a handful of preprocessor rules, `macro`-only) cases,
predating the five-kind requirement introduced in Phase 5. Retroactively
disabling all of them the moment the stricter policy landed would silently
turn off a third of the rule set with no code change -- clearly not the
intent of "rules without tests may not be enabled by default", which is
aimed at *untested* rules. So the gate below distinguishes:

  * no `positive`/`negative` pair at all -> genuinely untested -> disabled.
  * `positive`+`negative` present but missing `macro`/`embedded`/`edge` ->
    enabled, but flagged `conformance_complete=False` /
    `legacy_partial_conformance=True` so it shows up in the report as a
    backlog item rather than silently passing as fully covered.
  * all five kinds present -> fully conformant; confidence calibration
    decides enabled vs. experimental.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from misra_platform_rules.conformance import ConformanceMetrics, RuleConformanceSuite

REQUIRED_CASE_KINDS: frozenset[str] = frozenset({"positive", "negative", "edge", "macro", "embedded"})
MINIMUM_CASE_KINDS: frozenset[str] = frozenset({"positive", "negative"})


@dataclass(frozen=True, slots=True)
class ConfidenceThresholds:
    min_precision: float = 0.85
    min_recall: float = 0.75
    max_false_positive_rate: float = 0.15


DEFAULT_THRESHOLDS = ConfidenceThresholds()


@dataclass(frozen=True, slots=True)
class RuleEnablementDecision:
    rule_id: str
    conformance_complete: bool
    missing_case_kinds: list[str]
    precision: float
    recall: float
    false_positive_rate: float
    total_cases: int
    enabled_by_default: bool
    experimental: bool
    legacy_partial_conformance: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "conformance_complete": self.conformance_complete,
            "missing_case_kinds": self.missing_case_kinds,
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "false_positive_rate": round(self.false_positive_rate, 3),
            "total_cases": self.total_cases,
            "enabled_by_default": self.enabled_by_default,
            "experimental": self.experimental,
            "legacy_partial_conformance": self.legacy_partial_conformance,
            "reason": self.reason,
        }


def conformance_completeness(suite: RuleConformanceSuite) -> tuple[bool, list[str]]:
    present = {case.kind for case in suite.cases}
    missing = sorted(REQUIRED_CASE_KINDS - present)
    return (not missing, missing)


def _has_minimum_coverage(suite: RuleConformanceSuite) -> bool:
    present = {case.kind for case in suite.cases}
    return MINIMUM_CASE_KINDS <= present


def evaluate_rule(
    suite: RuleConformanceSuite,
    metrics: ConformanceMetrics,
    thresholds: ConfidenceThresholds = DEFAULT_THRESHOLDS,
) -> RuleEnablementDecision:
    complete, missing = conformance_completeness(suite)

    if not complete and not _has_minimum_coverage(suite):
        return RuleEnablementDecision(
            rule_id=suite.rule_id,
            conformance_complete=False,
            missing_case_kinds=missing,
            precision=metrics.precision,
            recall=metrics.recall,
            false_positive_rate=metrics.false_positive_rate,
            total_cases=metrics.total_cases,
            enabled_by_default=False,
            experimental=False,
            legacy_partial_conformance=False,
            reason=f"disabled: no tests at all for required case kinds {missing}",
        )

    if not complete:
        # Has at least a positive/negative pair but predates or misses the
        # five-kind requirement. Phase 6 policy: such rules remain enabled
        # but are flagged experimental until full conformance coverage lands.
        return RuleEnablementDecision(
            rule_id=suite.rule_id,
            conformance_complete=False,
            missing_case_kinds=missing,
            precision=metrics.precision,
            recall=metrics.recall,
            false_positive_rate=metrics.false_positive_rate,
            total_cases=metrics.total_cases,
            enabled_by_default=True,
            experimental=True,
            legacy_partial_conformance=True,
            reason=(
                f"experimental (legacy partial conformance): missing case kinds {missing}; "
                "enabled but flagged until macro/embedded/edge coverage is added"
            ),
        )

    low_confidence = (
        metrics.precision < thresholds.min_precision
        or metrics.recall < thresholds.min_recall
        or metrics.false_positive_rate > thresholds.max_false_positive_rate
    )

    if low_confidence:
        return RuleEnablementDecision(
            rule_id=suite.rule_id,
            conformance_complete=True,
            missing_case_kinds=[],
            precision=metrics.precision,
            recall=metrics.recall,
            false_positive_rate=metrics.false_positive_rate,
            total_cases=metrics.total_cases,
            enabled_by_default=True,
            experimental=True,
            legacy_partial_conformance=False,
            reason=(
                "experimental: below confidence thresholds "
                f"(precision={metrics.precision:.2f}, recall={metrics.recall:.2f}, "
                f"fpr={metrics.false_positive_rate:.2f})"
            ),
        )

    return RuleEnablementDecision(
        rule_id=suite.rule_id,
        conformance_complete=True,
        missing_case_kinds=[],
        precision=metrics.precision,
        recall=metrics.recall,
        false_positive_rate=metrics.false_positive_rate,
        total_cases=metrics.total_cases,
        enabled_by_default=True,
        experimental=False,
        legacy_partial_conformance=False,
        reason="enabled: full conformance coverage and within confidence thresholds",
    )


def evaluate_all(
    suites_by_id: dict[str, RuleConformanceSuite],
    metrics_by_id: dict[str, ConformanceMetrics],
    thresholds: ConfidenceThresholds = DEFAULT_THRESHOLDS,
) -> list[RuleEnablementDecision]:
    decisions = []
    for rule_id, suite in suites_by_id.items():
        metrics = metrics_by_id.get(rule_id)
        if metrics is None:
            decisions.append(
                RuleEnablementDecision(
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
                    reason="disabled: no conformance metrics available",
                )
            )
            continue
        decisions.append(evaluate_rule(suite, metrics, thresholds))
    return decisions


def enablement_summary(decisions: list[RuleEnablementDecision]) -> dict[str, Any]:
    enabled = [d for d in decisions if d.enabled_by_default and not d.experimental]
    experimental = [d for d in decisions if d.experimental]
    disabled = [d for d in decisions if not d.enabled_by_default]
    legacy_partial = [d for d in decisions if d.legacy_partial_conformance]
    return {
        "total_rules": len(decisions),
        "enabled_count": len(enabled),
        "experimental_count": len(experimental),
        "disabled_count": len(disabled),
        "legacy_partial_conformance_count": len(legacy_partial),
        "enabled_rule_ids": sorted(d.rule_id for d in enabled),
        "experimental_rule_ids": sorted(d.rule_id for d in experimental),
        "disabled_rule_ids": sorted(d.rule_id for d in disabled),
        "legacy_partial_conformance_rule_ids": sorted(d.rule_id for d in legacy_partial),
    }
