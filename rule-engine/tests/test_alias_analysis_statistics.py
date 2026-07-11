"""Phase 6.5: alias-analysis statistics report generation."""

from __future__ import annotations

import json
from pathlib import Path

from misra_platform_rules.alias_analysis_statistics import (
    _REPORT_NAMES,
    collect_statistics,
    write_alias_analysis_reports,
)

from conformance.fixtures import build_all_suites

_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _conformance_artifacts() -> list[dict]:
    artifacts: list[dict] = []
    for suite in build_all_suites():
        for case in suite.cases:
            artifacts.append(case.artifact)
    return artifacts


def test_collect_alias_statistics_from_conformance_artifacts() -> None:
    artifacts = _conformance_artifacts()
    stats = collect_statistics(artifacts)
    assert len(stats) == 2
    for name in _REPORT_NAMES:
        assert name in stats
        assert stats[name]["artifact_count"] == len(artifacts)


def test_write_alias_analysis_reports() -> None:
    artifacts = _conformance_artifacts()
    written = write_alias_analysis_reports(artifacts, _REPORTS_DIR)
    assert set(written.keys()) == set(_REPORT_NAMES)
    for path in written.values():
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "artifact_count" in payload
