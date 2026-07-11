"""Phase 6.1: analyzer efficiency metrics and preflight report generation.

Tracks whether shared analyzers respect the semantic-unit budget:

  * CFG / Alias / DataFlow — at most one build per function per TU run
  * SymbolIndex / LinkageIndex — at most one build per TU run

Produces machine-readable preflight artifacts:

  * ``cache_report.json`` — hit ratios, miss reasons, per-unit build counts
  * ``top_analyzer_costs.json`` — analyzers ranked by build volume and waste
  * ``reuse_report.json`` — per-rule shared-analyzer reuse percentages
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from misra_platform_rules import analyzer_reuse

# Miss reasons recorded on first access to a semantic unit.
MISS_REASON_FIRST_ACCESS = "first_access_for_semantic_unit"
MISS_REASON_DATAFLOW_DEPENDS_ON_ALIAS = "dataflow_engine_requires_alias_analysis"

ANALYZER_NAMES = (
    "cfg",
    "alias",
    "dataflow_engine",
    "dataflow_result",
    "symbol_index",
    "linkage_index",
    "linkage_analyzer",
)


@dataclass(frozen=True, slots=True)
class SemanticUnitBudget:
    """Maximum allowed builds per semantic unit for one TU run."""

    name: str
    scope: str  # "per_function" | "per_translation_unit"
    max_builds: int = 1


SEMANTIC_UNIT_BUDGETS: tuple[SemanticUnitBudget, ...] = (
    SemanticUnitBudget("cfg", "per_function"),
    SemanticUnitBudget("alias", "per_function"),
    SemanticUnitBudget("dataflow_engine", "per_function"),
    SemanticUnitBudget("symbol_index", "per_translation_unit"),
    SemanticUnitBudget("linkage_index", "per_translation_unit"),
)


def _hit_rate(hits: int, misses: int) -> float:
    total = hits + misses
    return round(hits / total, 4) if total else 0.0


def _budget_compliance(
    builds_per_unit: dict[str, int],
    *,
    budget: SemanticUnitBudget,
) -> dict[str, Any]:
    if not builds_per_unit:
        return {
            "analyzer": budget.name,
            "scope": budget.scope,
            "max_builds_allowed": budget.max_builds,
            "units_analyzed": 0,
            "total_builds": 0,
            "violations": 0,
            "compliant": True,
            "over_budget_units": [],
        }
    over = {unit_id: count for unit_id, count in builds_per_unit.items() if count > budget.max_builds}
    total_builds = sum(builds_per_unit.values())
    return {
        "analyzer": budget.name,
        "scope": budget.scope,
        "max_builds_allowed": budget.max_builds,
        "units_analyzed": len(builds_per_unit),
        "total_builds": total_builds,
        "violations": len(over),
        "compliant": not over,
        "over_budget_units": [
            {"unit_id": unit_id, "builds": count}
            for unit_id, count in sorted(over.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
    }


def _aggregate_per_function_builds(tu_stats: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Sum build counts only when the same function id appears in multiple TUs."""
    totals: dict[str, int] = defaultdict(int)
    for stats in tu_stats:
        for fn_id, count in stats.get(field, {}).items():
            totals[fn_id] += int(count)
    return dict(totals)


def _per_tu_budget_violations(
    tu_stats: list[dict[str, Any]],
    *,
    field: str,
    budget: SemanticUnitBudget,
) -> tuple[int, list[dict[str, Any]]]:
    violations = 0
    samples: list[dict[str, Any]] = []
    for index, stats in enumerate(tu_stats):
        for unit_id, count in stats.get(field, {}).items():
            if count > budget.max_builds:
                violations += 1
                if len(samples) < 10:
                    samples.append(
                        {
                            "translation_unit": f"tu-{index}",
                            "unit_id": unit_id,
                            "builds": count,
                        }
                    )
    return violations, samples


def aggregate_tu_efficiency_stats(tu_stats: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-translation-unit ``AnalysisCache.efficiency_stats()`` payloads."""
    hits = 0
    misses = 0
    hits_by_analyzer: Counter[str] = Counter()
    misses_by_analyzer: Counter[str] = Counter()
    miss_reasons: Counter[str] = Counter()
    symbol_index_builds = 0
    linkage_index_builds = 0
    linkage_analyzer_builds = 0
    symbol_index_builds_per_tu: dict[str, int] = {}
    linkage_index_builds_per_tu: dict[str, int] = {}
    cfg_builds_total = 0
    alias_builds_total = 0
    dataflow_builds_total = 0

    for index, stats in enumerate(tu_stats):
        tu_key = f"tu-{index}"
        hits += int(stats.get("hits", 0))
        misses += int(stats.get("misses", 0))
        for name, value in stats.get("hits_by_analyzer", {}).items():
            hits_by_analyzer[name] += int(value)
        for name, value in stats.get("misses_by_analyzer", {}).items():
            misses_by_analyzer[name] += int(value)
        for reason, value in stats.get("miss_reasons", {}).items():
            miss_reasons[reason] += int(value)
        cfg_builds_total += len(stats.get("cfg_builds_per_function", {}))
        alias_builds_total += len(stats.get("alias_builds_per_function", {}))
        dataflow_builds_total += len(stats.get("dataflow_builds_per_function", {}))
        tu_symbol_builds = int(stats.get("symbol_index_builds", 0))
        tu_linkage_builds = int(stats.get("linkage_index_builds", 0))
        symbol_index_builds += tu_symbol_builds
        linkage_index_builds += tu_linkage_builds
        linkage_analyzer_builds += int(stats.get("linkage_analyzer_builds", 0))
        symbol_index_builds_per_tu[tu_key] = tu_symbol_builds
        linkage_index_builds_per_tu[tu_key] = tu_linkage_builds

    hit_rates_by_analyzer = {
        name: _hit_rate(hits_by_analyzer.get(name, 0), misses_by_analyzer.get(name, 0))
        for name in ANALYZER_NAMES
        if hits_by_analyzer.get(name, 0) + misses_by_analyzer.get(name, 0) > 0
    }

    cfg_violations, cfg_over = _per_tu_budget_violations(
        tu_stats, field="cfg_builds_per_function", budget=SEMANTIC_UNIT_BUDGETS[0]
    )
    alias_violations, alias_over = _per_tu_budget_violations(
        tu_stats, field="alias_builds_per_function", budget=SEMANTIC_UNIT_BUDGETS[1]
    )
    dataflow_violations, dataflow_over = _per_tu_budget_violations(
        tu_stats, field="dataflow_builds_per_function", budget=SEMANTIC_UNIT_BUDGETS[2]
    )

    def _redundant_builds(field: str) -> int:
        redundant = 0
        for stats in tu_stats:
            for count in stats.get(field, {}).values():
                redundant += max(0, int(count) - 1)
        return redundant

    redundant_cfg = _redundant_builds("cfg_builds_per_function")
    redundant_alias = _redundant_builds("alias_builds_per_function")
    redundant_dataflow = _redundant_builds("dataflow_builds_per_function")

    budgets = {
        "cfg": {
            **_budget_compliance({}, budget=SEMANTIC_UNIT_BUDGETS[0]),
            "units_analyzed": cfg_builds_total,
            "total_builds": cfg_builds_total,
            "violations": cfg_violations,
            "compliant": cfg_violations == 0,
            "over_budget_units": cfg_over,
        },
        "alias": {
            **_budget_compliance({}, budget=SEMANTIC_UNIT_BUDGETS[1]),
            "units_analyzed": alias_builds_total,
            "total_builds": alias_builds_total,
            "violations": alias_violations,
            "compliant": alias_violations == 0,
            "over_budget_units": alias_over,
        },
        "dataflow_engine": {
            **_budget_compliance({}, budget=SEMANTIC_UNIT_BUDGETS[2]),
            "units_analyzed": dataflow_builds_total,
            "total_builds": dataflow_builds_total,
            "violations": dataflow_violations,
            "compliant": dataflow_violations == 0,
            "over_budget_units": dataflow_over,
        },
        "symbol_index": _budget_compliance(
            symbol_index_builds_per_tu,
            budget=SemanticUnitBudget("symbol_index", "per_translation_unit"),
        ),
        "linkage_index": _budget_compliance(
            linkage_index_builds_per_tu,
            budget=SemanticUnitBudget("linkage_index", "per_translation_unit"),
        ),
    }
    redundant_builds = {
        "cfg": redundant_cfg,
        "alias": redundant_alias,
        "dataflow_engine": redundant_dataflow,
        "symbol_index": sum(
            max(0, count - 1) for count in symbol_index_builds_per_tu.values()
        ),
        "linkage_index": sum(
            max(0, count - 1) for count in linkage_index_builds_per_tu.values()
        ),
    }

    return {
        "hits": hits,
        "misses": misses,
        "hit_rate": _hit_rate(hits, misses),
        "hits_by_analyzer": dict(hits_by_analyzer),
        "misses_by_analyzer": dict(misses_by_analyzer),
        "hit_rates_by_analyzer": hit_rates_by_analyzer,
        "miss_reasons": dict(miss_reasons),
        "cfg_builds_per_function": _aggregate_per_function_builds(tu_stats, "cfg_builds_per_function"),
        "alias_builds_per_function": _aggregate_per_function_builds(tu_stats, "alias_builds_per_function"),
        "dataflow_builds_per_function": _aggregate_per_function_builds(
            tu_stats, "dataflow_builds_per_function"
        ),
        "symbol_index_builds_per_project": symbol_index_builds,
        "linkage_index_builds_per_project": linkage_index_builds,
        "linkage_analyzer_builds": linkage_analyzer_builds,
        "cfgs_built": cfg_builds_total,
        "alias_analyses_run": alias_builds_total,
        "dataflow_engines_built": dataflow_builds_total,
        "translation_units_with_cache": len(tu_stats),
        "semantic_unit_budgets": budgets,
        "redundant_builds": redundant_builds,
        "all_budgets_met": all(
            budgets[key]["compliant"]
            for key in ("cfg", "alias", "dataflow_engine", "symbol_index", "linkage_index")
        ),
    }


def build_cache_report(
    *,
    translation_unit_stats: dict[str, dict[str, Any]] | None = None,
    aggregate: dict[str, Any] | None = None,
    label: str = "",
) -> dict[str, Any]:
    tu_stats = translation_unit_stats or {}
    agg = aggregate or aggregate_tu_efficiency_stats(list(tu_stats.values()))
    return {
        "label": label,
        "aggregate": agg,
        "per_translation_unit": {
            tu_id: stats for tu_id, stats in sorted(tu_stats.items())
        },
        "cache_hit_ratios": {
            "overall": agg.get("hit_rate", 0.0),
            "by_analyzer": agg.get("hit_rates_by_analyzer", {}),
        },
        "cache_miss_reasons": agg.get("miss_reasons", {}),
        "semantic_unit_compliance": agg.get("semantic_unit_budgets", {}),
        "all_semantic_unit_budgets_met": agg.get("all_budgets_met", True),
    }


def build_top_analyzer_costs(
    aggregate: dict[str, Any],
    *,
    rule_timings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rank analyzers by build volume (primary cost proxy) and surface waste."""
    ranked: list[dict[str, Any]] = []
    budgets = aggregate.get("semantic_unit_budgets", {})
    redundant = aggregate.get("redundant_builds", {})
    for analyzer in ("cfg", "alias", "dataflow_engine", "symbol_index", "linkage_index", "linkage_analyzer"):
        if analyzer == "cfg":
            builds = int(aggregate.get("cfgs_built", 0))
        elif analyzer == "alias":
            builds = int(aggregate.get("alias_analyses_run", 0))
        elif analyzer == "dataflow_engine":
            builds = int(aggregate.get("dataflow_engines_built", 0))
        elif analyzer == "symbol_index":
            builds = int(aggregate.get("symbol_index_builds_per_project", 0))
        elif analyzer == "linkage_index":
            builds = int(aggregate.get("linkage_index_builds_per_project", 0))
        else:
            builds = int(aggregate.get("linkage_analyzer_builds", 0))

        hits = int(aggregate.get("hits_by_analyzer", {}).get(analyzer, 0))
        misses = int(aggregate.get("misses_by_analyzer", {}).get(analyzer, 0))
        budget_key = analyzer if analyzer != "linkage_analyzer" else None
        violations = int(budgets.get(budget_key, {}).get("violations", 0)) if budget_key else 0
        redundant_builds = int(redundant.get(analyzer, 0))

        ranked.append(
            {
                "analyzer": analyzer,
                "total_builds": builds,
                "cache_hits": hits,
                "cache_misses": misses,
                "hit_rate": _hit_rate(hits, misses),
                "semantic_unit_violations": violations,
                "redundant_builds": redundant_builds,
                "cost_score": builds + redundant_builds,
            }
        )

    ranked.sort(key=lambda entry: entry["cost_score"], reverse=True)

    rule_ranked = []
    if rule_timings:
        rule_ranked = sorted(
            rule_timings,
            key=lambda entry: float(entry.get("total_duration_ms", 0.0)),
            reverse=True,
        )[:15]

    return {
        "ranked_by_analyzer_cost": ranked,
        "top_rule_durations_ms": rule_ranked,
        "primary_cost_driver": ranked[0]["analyzer"] if ranked else None,
    }


def build_reuse_report(rule_ids: list[str]) -> dict[str, Any]:
    """Reuse percentages per rule and by analyzer category."""
    summary = analyzer_reuse.reuse_summary(rule_ids)
    entries = summary.get("entries", [])
    category_usage: Counter[str] = Counter()
    for entry in entries:
        for category in entry.get("categories", []):
            category_usage[category] += 1

    total = len(rule_ids)
    category_percentages = {
        category: round(count / total, 4) if total else 0.0
        for category, count in sorted(category_usage.items())
    }

    return {
        **summary,
        "reuse_percentage": round(summary.get("reuse_rate", 0.0) * 100, 1),
        "category_reuse_counts": dict(category_usage),
        "category_reuse_percentages": category_percentages,
        "rules_without_shared_analyzers": summary.get("rules_with_no_recorded_usage", []),
    }


def write_preflight_reports(
    output_dir: Path,
    *,
    cache_report: dict[str, Any],
    top_costs: dict[str, Any],
    reuse_report: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "cache_report": output_dir / "cache_report.json",
        "top_analyzer_costs": output_dir / "top_analyzer_costs.json",
        "reuse_report": output_dir / "reuse_report.json",
    }
    paths["cache_report"].write_text(json.dumps(cache_report, indent=2), encoding="utf-8")
    paths["top_analyzer_costs"].write_text(json.dumps(top_costs, indent=2), encoding="utf-8")
    paths["reuse_report"].write_text(json.dumps(reuse_report, indent=2), encoding="utf-8")
    return paths


def project_cache_report_from_execution(
    project_report: Any,
    *,
    label: str = "",
) -> dict[str, Any]:
    """Build a cache report from a ``ProjectExecutionReport``."""
    tu_stats: dict[str, dict[str, Any]] = {}
    for tu_id, tu_report in project_report.translation_unit_reports.items():
        if tu_report.cache_stats:
            tu_stats[tu_id] = dict(tu_report.cache_stats)
    aggregate = aggregate_tu_efficiency_stats(list(tu_stats.values()))
    return build_cache_report(
        translation_unit_stats=tu_stats,
        aggregate=aggregate,
        label=label,
    )
