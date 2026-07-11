# Phase 6.2 — AST-Only `ready_now` Batch (25 Rules)

Phase 6.1 validated analyzer budgets and cache hit ratios. Phase 6.2
implements the full **AST-only `ready_now` batch** (25 rules) using only
existing infrastructure — no new analyzers.

**Rule count: 75 → 100** (+25), all with full five-kind conformance suites.

## 1. Batch Implemented

| Pack | Rules | Shared infrastructure |
|---|---|---|
| **Preprocessor** | 20.1, 20.2, 20.3, 20.6, 20.8, 20.9, 20.11, 20.12, 20.13, 17.1, 21.4, 21.5, 21.10, 21.11, 21.12 | `MacroAnalyzer` |
| **Standard library** | 21.3, 21.6, 21.7, 21.8, 21.9, 21.21, 22.8 | `ASTQuery` + `MacroAnalyzer` (headers) |
| **Expressions** | 13.3, 17.7 | `ExpressionClassifier` |
| **Control flow** | 2.6 | `CFGBuilder` (`cfg().labels()` / `goto_targets()`) |

New module: `rule_pack_standard_library.py` (stdlib/header/call bans).

Extended: `macro_analyzer.py`, `expression_classifier.py`,
`rule_pack_preprocessor.py`, `rule_pack_expressions.py`,
`rule_pack_control_flow.py`.

## 2. Conformance

All 25 rules ship five-kind suites in `fixtures_phase62.py` (125 new cases).
None are experimental — all 25 are fully conformant and enabled.

| Metric | Before (6.1) | After (6.2) |
|---|---|---|
| Fully conformant (non-experimental) | 39 | **64** |
| Experimental (legacy partial) | 36 | 36 |
| Disabled | 0 | 0 |

## 3. Coverage & Roadmap

| Metric | Value |
|---|---|
| **Implemented** | **100** |
| **Catalog total** | 158 |
| **Coverage** | **63.3%** |
| `ready_now` ast_only remaining | **0** (batch complete) |
| `ready_now` total remaining | **32** |

Next batch per `rule_batch_planner.py`: **type_system** (14 rules).

## 4. Benchmark Delta

Synthetic baseline (18K LOC, 30 TUs, 1200 functions):

| Metric | 75 rules (6.1) | 100 rules (6.2) | Delta |
|---|---|---|---|
| Duration | 698 ms | **649 ms** | −7% |
| Rule count | 75 | 100 | +33% |
| Throughput | 25,782 LOC/s | **27,715 LOC/s** | +7.5% |
| 100K LOC projection | 3.88 s | **3.61 s** | meets target |
| Cache hit rate | 43.8% | **43.8%** | no regression |

AST-only rules add negligible wall time; variance dominates the small
apparent speedup. No semantic-unit budget violations.

## 5. Top New Rule Costs

Only one Phase 6.2 rule entered the top-10 slowest list:

| Rule | Total ms (30 TUs) | Avg ms/TU | Analyzer |
|---|---|---|---|
| **2.6** (unused labels) | 17.6 | 0.59 | `CFGBuilder` label/goto scan |

All other Phase 6.2 rules are preprocessor/stdlib AST scans with sub-ms
per-TU cost and do not appear in the top-10.

## 6. Analyzer Efficiency

| Check | Result |
|---|---|
| Semantic unit budgets | **0 violations** |
| Analyzer reuse | **100%** (100/100) |
| Cache hit rate | **43.8%** (unchanged) |
| Crashes (embedded corpus) | **0** (1200 rule/function pairs) |

## 7. Unsupported Constructs Discovered

Phase 6.2 rules surface no new crash classes. Metadata-driven detection
relies on preprocessor fields already serialized by clang-worker:

- `include_directives` with `header`, `is_well_formed`, `preceded_only_by_preprocessor`
- `conditional_branches` with `controlling_expression_valid`, `undefined_identifiers`
- `preprocessor_directives` with `is_permitted_form`
- `CallExpr.semantic_properties` with `callee`, `requires_errno_clear`, `errno_cleared`

**Gap (documented, not blocking):** Rules 20.6/20.11/20.12 depend on macro-body
token-shape metadata; full fidelity requires raw macro-body text from
clang-worker (same gap as Dir 4.9 / Rule 20.10). Current implementation
uses structured `macro_definitions` fields populated by the serializer.

## 8. Verification

```bash
cd rule-engine && python -m pytest -q                     # 102 passed
cd rule-engine && python -m ruff check src tests

# Regenerate reports:
python -m pytest tests/conformance -q
python -m pytest tests/performance -q
python -m pytest tests/conformance/test_embedded_corpora.py -q
```

Reports updated under `rule-engine/reports/` and `tests/performance/performance_report.json`.
