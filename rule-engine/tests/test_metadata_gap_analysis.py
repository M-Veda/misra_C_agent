"""Phase 7: metadata gap report generation and regression guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from misra_platform_rules.metadata_gap_analysis import (
    PHASE_7_AST_SCHEMA_VERSION,
    build_gap_entries,
    build_metadata_gap_report,
    build_phase_7_1_benchmark_report,
    write_metadata_gap_report,
)

_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def test_blocked_rules_have_gap_entries() -> None:
    entries = build_gap_entries()
    assert len(entries) == 1
    identifiers = {entry.identifier for entry in entries}
    assert identifiers == {"4.2"}


def test_metadata_gap_report_structure() -> None:
    report = build_metadata_gap_report()
    assert report["ast_schema_version"] == PHASE_7_AST_SCHEMA_VERSION
    assert report["blocked_on_ast_metadata_before"] == 1
    assert report["gaps_resolved"] == 0
    assert report["gaps_partial"] == 1
    assert report["newly_unblocked_count"] == 0
    assert len(report["rules"]) == 1
    assert "serialization_growth_estimate" in report


def test_write_metadata_gap_report() -> None:
    path = write_metadata_gap_report(_REPORTS_DIR)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["implemented_rules"] == 152
    assert "phase_7_ast_field_catalog" in payload
    assert "phase_7_preprocessor_field_catalog" in payload


def test_phase_7_1_rule_count() -> None:
    """Phase 7.1 implements 20 metadata-unblocked rules (132 -> 152)."""
    from misra_platform_rules.registry import create_default_registry

    registry = create_default_registry()
    assert len(registry.list_rule_ids()) == 152


def test_phase_7_1_benchmark_report() -> None:
    report = build_phase_7_1_benchmark_report()
    assert report["rules_added"] == 20
    assert report["implemented_rules"] == 152
    assert report["coverage_percent"] == 96.2
    assert report["cache_budget_violations"] == 0


def test_phase_71_conformance_suite_size() -> None:
    from conformance.fixtures_phase71 import PHASE71_SUITE_BUILDERS

    assert len(PHASE71_SUITE_BUILDERS) == 20
    suites = [builder() for builder in PHASE71_SUITE_BUILDERS]
    assert sum(len(suite.cases) for suite in suites) == 100


def test_rule_4_2_still_blocked_after_phase_7_1() -> None:
    report = build_metadata_gap_report()
    entry = next(item for item in report["rules"] if item["rule_id"] == "misra-c2012-rule-4-2")
    assert entry["resolution_status"] == "partial"
    assert entry["projected_tier_after_phase_7"] == "blocked_on_ast_metadata"
