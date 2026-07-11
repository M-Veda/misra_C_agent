"""Conformance harness: runs labeled test cases against a rule plugin and
computes precision / recall / false-positive rate.

A `ConformanceCase` is a minimal synthetic AST artifact plus a label of
whether the rule is expected to fire. Cases are tagged by `kind` (positive,
negative, edge, macro, embedded) purely for reporting/organization — the
metrics computation only cares about `expects_violation`.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from misra_platform_rules.base_rule import IRulePlugin
from misra_platform_rules.rule_context import RuleContext

CaseKind = Literal["positive", "negative", "edge", "macro", "embedded"]


@dataclass(slots=True)
class ConformanceCase:
    case_id: str
    kind: CaseKind
    artifact: dict[str, Any]
    expects_violation: bool
    description: str = ""
    cross_tu_linkage: dict[str, Any] | None = None


@dataclass(slots=True)
class RuleConformanceSuite:
    rule_id: str
    cases: list[ConformanceCase] = field(default_factory=list)


@dataclass(slots=True)
class CaseOutcome:
    case_id: str
    kind: CaseKind
    expected: bool
    actual: bool
    correct: bool


@dataclass(slots=True)
class ConformanceMetrics:
    rule_id: str
    total_cases: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    outcomes: list[CaseOutcome] = field(default_factory=list)

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def false_positive_rate(self) -> float:
        denominator = self.false_positives + self.true_negatives
        return self.false_positives / denominator if denominator else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "total_cases": self.total_cases,
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "false_positive_rate": round(self.false_positive_rate, 3),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
        }


class ConformanceRunner:
    def run(self, plugin: IRulePlugin, suite: RuleConformanceSuite) -> ConformanceMetrics:
        tp = fp = tn = fn = 0
        outcomes: list[CaseOutcome] = []

        for case in suite.cases:
            context = RuleContext.from_ast_artifact(
                artifact=case.artifact,
                translation_unit_id=case.case_id,
                cross_tu_linkage=case.cross_tu_linkage,
            )
            violations = plugin.detect(context)
            fired = len(violations) > 0

            if case.expects_violation and fired:
                tp += 1
            elif case.expects_violation and not fired:
                fn += 1
            elif not case.expects_violation and fired:
                fp += 1
            else:
                tn += 1

            outcomes.append(
                CaseOutcome(
                    case_id=case.case_id,
                    kind=case.kind,
                    expected=case.expects_violation,
                    actual=fired,
                    correct=(case.expects_violation == fired),
                )
            )

        return ConformanceMetrics(
            rule_id=suite.rule_id,
            total_cases=len(suite.cases),
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
            outcomes=outcomes,
        )

    def run_all(
        self, plugins_by_id: dict[str, IRulePlugin], suites: list[RuleConformanceSuite]
    ) -> list[ConformanceMetrics]:
        results = []
        for suite in suites:
            plugin = plugins_by_id.get(suite.rule_id)
            if not plugin:
                continue
            results.append(self.run(plugin, suite))
        return results
