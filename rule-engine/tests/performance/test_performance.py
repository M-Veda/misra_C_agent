"""Phase 3 performance benchmark test.

Runs the full 36-rule set against a modest synthetic project, extrapolates
to the 100K/500K LOC and incremental-analysis targets, and writes
`performance_report.json` next to this file. See `docs/PHASE_3.md` for the
target numbers and methodology caveats.
"""

import json
from pathlib import Path

from benchmark_rule_engine import generate_report


def test_performance_report_meets_targets() -> None:
    report = generate_report(baseline_tus=30, functions_per_tu=40)

    output_path = Path(__file__).with_name("performance_report.json")
    output_path.write_text(json.dumps(report, indent=2))

    assert report["baseline"]["loc"] > 0
    assert report["projections"]["100k_loc_meets_target"] is True
    assert report["projections"]["500k_loc_meets_target"] is True
    assert report["incremental"]["meets_target"] is True
