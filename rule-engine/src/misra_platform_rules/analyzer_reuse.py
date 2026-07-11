"""Analyzer reuse tracking (Phase 5).

Policy: no rule plugin may implement type reasoning, CFG traversal, alias
logic, or dataflow logic internally. Every rule must obtain those facts
through the shared analyzers exposed as accessor methods on
`BaseRulePlugin` (`essential_types()`, `cfg_v2()`, `aliases()`,
`dataflow_v2()`, etc.).

Rather than relying on that policy being followed by convention alone, this
module gives `BaseRulePlugin` a lightweight, process-wide usage ledger: every
time a rule calls one of the shared-analyzer accessors, the call is recorded
against the rule's id. This lets us build a reuse report showing exactly
which shared services each rule depends on, and flag any rule that appears
to do no analyzer-backed reasoning at all (i.e. pure boolean/string
AST-shape matching with no shared semantic analysis).

The ledger is process-global by design: rules are stateless plugin
singletons and conformance/production runs exercise `detect()` many times
per process, so accumulating usage across calls is what we want. Tests that
need a clean slate should call `reset()`.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

_USAGE_LOG: dict[str, set[str]] = defaultdict(set)

# Maps each BaseRulePlugin accessor name to the capability category it
# provides, for reporting/roadmap purposes. Kept separate from
# `rule_capability_matrix.py`'s capability taxonomy since this describes
# *actual observed usage* rather than *declared requirements*.
ANALYZER_CATEGORIES: dict[str, str] = {
    "graph": "ast-query",
    "essential_types": "type-system",
    "essential_types_v2": "type-system",
    "casts": "type-system",
    "qualifiers": "type-system",
    "pointers": "pointer-heuristics",
    "cfg": "control-flow",
    "cfg_v2": "control-flow",
    "dataflow": "dataflow",
    "dataflow_v2": "dataflow",
    "aliases": "alias-analysis",
    "symbols": "symbol-index",
    "linkage": "cross-tu",
    "linkage_analyzer": "cross-tu",
    "macros": "preprocessor",
    "expressions": "expression-classification",
}


def record_usage(rule_id: str, analyzer_name: str) -> None:
    _USAGE_LOG[rule_id].add(analyzer_name)


def usage_for(rule_id: str) -> set[str]:
    return set(_USAGE_LOG.get(rule_id, set()))


def reset() -> None:
    _USAGE_LOG.clear()


def snapshot() -> dict[str, set[str]]:
    return {rule_id: set(names) for rule_id, names in _USAGE_LOG.items()}


@dataclass(slots=True)
class ReuseReportEntry:
    rule_id: str
    analyzers_used: list[str]
    categories: list[str]

    @property
    def reuses_shared_analysis(self) -> bool:
        return len(self.analyzers_used) > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "analyzers_used": self.analyzers_used,
            "categories": self.categories,
            "reuses_shared_analysis": self.reuses_shared_analysis,
        }


def build_reuse_report(rule_ids: list[str]) -> list[ReuseReportEntry]:
    """Builds a per-rule reuse entry from whatever usage has been recorded
    so far. Callers typically exercise each rule's `detect()` (e.g. via the
    conformance suites) before calling this, so that usage has actually been
    observed rather than merely declared."""
    entries = []
    for rule_id in rule_ids:
        used = sorted(usage_for(rule_id))
        categories = sorted({ANALYZER_CATEGORIES.get(name, "other") for name in used})
        entries.append(ReuseReportEntry(rule_id=rule_id, analyzers_used=used, categories=categories))
    return entries


def reuse_summary(rule_ids: list[str]) -> dict[str, Any]:
    entries = build_reuse_report(rule_ids)
    reusing = [e for e in entries if e.reuses_shared_analysis]
    not_reusing = [e for e in entries if not e.reuses_shared_analysis]
    return {
        "total_rules": len(entries),
        "rules_using_shared_analyzers": len(reusing),
        "rules_with_no_recorded_usage": [e.rule_id for e in not_reusing],
        "reuse_rate": round(len(reusing) / len(entries), 3) if entries else 0.0,
        "entries": [e.as_dict() for e in entries],
    }
