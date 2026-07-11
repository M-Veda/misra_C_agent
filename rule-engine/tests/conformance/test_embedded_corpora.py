"""Phase 4 deliverable: run the full rule registry against the
STM32-HAL/CMSIS/FreeRTOS/lwIP-modeled corpora and report crashes, findings,
and documented unsupported constructs.

The hard requirement is zero crashes: every registered rule must be able to
run against every realistic embedded-C construct in the corpus without
raising. Findings (rule firings) are recorded as data for the report, not
asserted against, because several of these patterns (register-access
pointer casts, buffer pointer arithmetic) are *real, expected* MISRA
findings in production embedded code -- documented deviations, not bugs in
the rule engine.
"""

import json
import traceback
from pathlib import Path

import pytest

from conformance.embedded_corpora import (
    KNOWN_CORPUS_ARTIFACT_RULES,
    UNSUPPORTED_CONSTRUCTS,
    build_all_corpora,
)
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_context import RuleContext

_REPORT_PATH = Path(__file__).resolve().parent / "embedded_corpus_report.json"


def _run_corpus_pass() -> dict:
    registry = create_default_registry()
    plugins = {rule_id: registry.get(rule_id) for rule_id in registry.list_rule_ids()}
    corpus_units = build_all_corpora()

    crashes: list[dict] = []
    findings: list[dict] = []

    for unit in corpus_units:
        context = RuleContext.from_ast_artifact(
            artifact=unit.artifact,
            translation_unit_id=f"{unit.corpus}/{unit.function_name}",
        )
        for rule_id, plugin in plugins.items():
            try:
                violations = plugin.detect(context)
            except Exception as error:  # noqa: BLE001 - intentionally broad: crash-safety survey
                crashes.append(
                    {
                        "corpus": unit.corpus,
                        "function": unit.function_name,
                        "rule_id": rule_id,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "traceback": traceback.format_exc(),
                    }
                )
                continue
            if violations:
                findings.append(
                    {
                        "corpus": unit.corpus,
                        "function": unit.function_name,
                        "rule_id": rule_id,
                        "violation_count": len(violations),
                    }
                )

    real_findings = [f for f in findings if f["rule_id"] not in KNOWN_CORPUS_ARTIFACT_RULES]
    artifact_findings = [f for f in findings if f["rule_id"] in KNOWN_CORPUS_ARTIFACT_RULES]

    findings_by_corpus: dict[str, int] = {}
    for finding in real_findings:
        findings_by_corpus[finding["corpus"]] = findings_by_corpus.get(finding["corpus"], 0) + 1

    return {
        "functions_analyzed": len(corpus_units),
        "rules_run": len(plugins),
        "crashes": crashes,
        "crash_count": len(crashes),
        "findings": real_findings,
        "finding_count": len(real_findings),
        "findings_by_corpus": findings_by_corpus,
        "corpus_construction_artifacts": {
            "findings": artifact_findings,
            "count": len(artifact_findings),
            "explanation": KNOWN_CORPUS_ARTIFACT_RULES,
        },
        "unsupported_constructs": UNSUPPORTED_CONSTRUCTS,
    }


@pytest.fixture(scope="module")
def corpus_report() -> dict:
    report = _run_corpus_pass()
    _REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def test_no_crashes_across_full_registry(corpus_report: dict) -> None:
    assert corpus_report["crash_count"] == 0, json.dumps(corpus_report["crashes"], indent=2)


def test_corpus_covers_all_four_codebases(corpus_report: dict) -> None:
    corpora = {unit.corpus for unit in build_all_corpora()}
    assert corpora == {"stm32_hal", "cmsis", "freertos", "lwip"}


def test_report_is_generated_on_disk(corpus_report: dict) -> None:
    assert _REPORT_PATH.exists()
    on_disk = json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    assert on_disk["rules_run"] == corpus_report["rules_run"]
