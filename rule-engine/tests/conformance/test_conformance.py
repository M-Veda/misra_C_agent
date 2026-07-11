import json
from pathlib import Path

import pytest

from conformance.fixtures import build_all_suites
from misra_platform_rules.conformance import ConformanceRunner
from misra_platform_rules.registry import create_default_registry

_REPORT_PATH = Path(__file__).resolve().parent / "conformance_report.json"


@pytest.fixture(scope="module")
def suites():
    return build_all_suites()


@pytest.fixture(scope="module")
def plugins():
    registry = create_default_registry()
    return {rule_id: registry.get(rule_id) for rule_id in registry.list_rule_ids()}


def test_every_suite_case_matches_expectation(suites, plugins) -> None:
    runner = ConformanceRunner()
    failures: list[str] = []

    for suite in suites:
        plugin = plugins.get(suite.rule_id)
        assert plugin is not None, f"{suite.rule_id} is not registered"
        metrics = runner.run(plugin, suite)
        for outcome in metrics.outcomes:
            if not outcome.correct:
                failures.append(
                    f"{suite.rule_id}/{outcome.case_id}: expected violation={outcome.expected}, "
                    f"got={outcome.actual}"
                )

    assert not failures, "Conformance mismatches:\n" + "\n".join(failures)


def test_conformance_report_generation(suites, plugins) -> None:
    runner = ConformanceRunner()
    report = []
    for suite in suites:
        plugin = plugins.get(suite.rule_id)
        if plugin is None:
            continue
        metrics = runner.run(plugin, suite)
        report.append(metrics.as_dict())

    _REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    assert report
    average_precision = sum(item["precision"] for item in report) / len(report)
    average_recall = sum(item["recall"] for item in report) / len(report)
    assert average_precision >= 0.95
    assert average_recall >= 0.95
