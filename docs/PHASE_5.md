# Phase 5 — Scaling Toward Full MISRA C:2012 Coverage

Phase 4 built the semantic infrastructure (real CFG, dataflow v2, alias
analysis, essential-type v2, linkage analyzer) but kept rule count flat at
37. Phase 5's mandate is the opposite: **use that infrastructure to add
rule count, without sacrificing correctness** — every new rule must reuse a
shared analyzer, every new rule must ship with the full five-kind
conformance suite, and confidence is measured, not assumed.

**Rule count: 37 → 59** (+22), all backed by conformance suites, all
reusing shared analyzers, all validated with zero crashes against
STM32 HAL / CMSIS / FreeRTOS / lwIP idioms.

## 1. Rule Batch Generation Strategy

`rule_capability_matrix.py`'s live roadmap (regenerated from
`coverage_matrix.py`, not hand-maintained) was the input for batch
selection. 22 rules were picked across the six analysis-type batches the
brief specifies, prioritizing rules that were already `ready_now` (shared
analyzer exists, just needed a rule class) and that filled out an entire
MISRA rule pack rather than being scattered one-offs:

| Batch | Rules added | Shared analyzer(s) exercised |
|---|---|---|
| **A — AST-only** | 5.2, 5.3, 2.7, 13.1, 13.6, 16.2, 16.5, 21.2 | `SymbolIndex`, `ExpressionClassifier`, `MacroAnalyzer` |
| **B — Type-system** | 7.4, 11.1, 11.6, 18.3, 18.4 | `QualifierAnalyzer`, `CastAnalyzer`, `PointerAnalyzer` |
| **C — CFG** | 17.4, 15.4 (+ retrofit of 2.1, see §3) | `CFGBuilder`, `CFGEngine` |
| **D — Dataflow/alias** | 19.1 | `AliasAnalyzer` |
| **E — Cross-TU / linkage** | 5.8, 5.9, 8.5, 8.8 | `LinkageIndex`, `SymbolIndex` |
| **F — Preprocessor** | 2.5, 5.4 | `MacroAnalyzer` |

(18.4 and 11.1/11.6 sit in the type-system batch because their correctness
hinges on essential-type/pointer-type category comparisons, even though the
brief's "pointers" pack label also applies — rules are cross-referenced by
both `implementation_category` and `rule_pack` in `coverage_matrix.py`.)

## 2. Shared Analyzer Reuse

**Policy → code, not just convention.** `BaseRulePlugin`'s shared-analyzer
accessors (`essential_types()`, `cfg_v2()`, `aliases()`, `linkage_analyzer()`,
…) now record every call into a process-wide ledger
(`rule-engine/src/misra_platform_rules/analyzer_reuse.py`), keyed by the
calling rule's id. This turns "no rule reimplements type/CFG/alias/dataflow
logic" from an unenforced convention into something measurable:

- `analyzer_reuse.build_reuse_report(rule_ids)` — per-rule list of which
  accessors were actually invoked, categorized (`type-system`,
  `control-flow`, `dataflow`, `alias-analysis`, `cross-tu`, `preprocessor`, …).
- `tests/conformance/test_rule_enablement_and_reuse.py::test_analyzer_reuse_report`
  exercises every rule's `detect()` via its conformance suite and writes
  `rule-engine/reports/analyzer_reuse.json`.

**Result: 45/59 rules (76.3%) recorded shared-analyzer usage.** The
remaining 14 (e.g. Rule 16.2 "switch label only within its switch's
compound statement", Rule 16.4 "every switch has a default") are
legitimate pure AST-shape matches — checking a parent-chain relationship or
counting sibling nodes needs no type/CFG/dataflow reasoning, so recording
zero analyzer calls for them is correct, not a policy violation. The report
is tracked so this ratio can be watched as future batches land, rather than
asserted as a hard gate (a rule that's *correctly* AST-only shouldn't be
forced to call an analyzer it doesn't need).

Tests: `rule-engine/src/misra_platform_rules/analyzer_reuse.py` wired into
`rule_base.py`; report generation in
`tests/conformance/test_rule_enablement_and_reuse.py`.

## 3. Conformance Testing

**Every rule shipped in Phase 5 (22 new + the Phase 4 CFG rule 2.1, which
had shipped with zero conformance cases at all — closed here) has all five
required case kinds: `positive`, `negative`, `macro`, `embedded`, `edge`.**

`rule-engine/src/misra_platform_rules/rule_enablement.py` turns "rules
without tests may not be enabled by default" into an executable gate:

- `conformance_completeness(suite)` — checks all five kinds are present.
- **Grandfathering, not silent mass-disablement:** the 36 rules shipped in
  Phases 1–4 predate the five-kind requirement and have only `positive`/
  `negative` cases (a handful of preprocessor rules had their case `kind`
  fields corrected from a mislabeled `"macro"` to `"positive"`/`"negative"`
  during this audit — see `fixtures.py` rules 20.4/20.7/20.14/21.1). Rather
  than retroactively disabling a third of the rule set the moment the
  stricter policy landed, `evaluate_rule()` distinguishes:
  - no `positive`/`negative` pair at all → **disabled** (genuinely untested).
  - `positive`/`negative` present but missing `macro`/`embedded`/`edge` →
    **enabled**, flagged `legacy_partial_conformance=True` (tracked backlog
    item, not silently treated as equivalent to full coverage).
  - all five kinds present → confidence calibration (§4) decides
    enabled vs. experimental.
- `tests/conformance/test_rule_enablement_and_reuse.py::test_rule_enablement_report`
  runs every registered rule's suite through `ConformanceRunner` and writes
  `rule-engine/reports/rule_enablement.json`.

**Also closed:** Rule 2.1 (`misra-c2012-rule-2-1`, unreachable code) was
registered in Phase 4 but had *no* conformance suite whatsoever — a gap
this audit's own gate immediately caught. A full 5-kind suite was added
(`fixtures.py::rule_2_1`): dead code after `return`, a macro-expanded
logging call after `return`, an HAL-style if/else-both-return pattern, and
an empty-body edge case.

## 4. Rule Confidence Calibration

`rule_enablement.ConfidenceThresholds` (`min_precision=0.85`,
`min_recall=0.75`, `max_false_positive_rate=0.15`) is applied to every
conformance-complete rule's measured metrics
(`misra_platform_rules.conformance.ConformanceMetrics`, computed by
actually running `detect()` against every case, not estimated).

**Result: 59/59 rules score 100% precision, 100% recall, 0% false-positive
rate** across 187 total conformance cases
(`rule-engine/tests/conformance/conformance_report.json`) — **0 rules
downgraded to experimental.** This is expected at this stage: conformance
cases are synthetic, hand-built, unambiguous positive/negative pairs (that's
what makes them suitable as a gate at all), so a rule that fails one is a
correctness bug, not marginal calibration. The calibration machinery exists
so that once review-acceptance-rate data flows in from real usage (tracked
today via `backend/src/misra_platform/services/metrics_service.py`'s
`review_acceptance_rate()` — see Phase 2), a rule with high conformance
precision but a low *real-world* acceptance rate can still be flagged
experimental without a code change, purely from the metrics feed.

## 5. Rule Packs

All 22 new rules landed inside existing `RulePack` groupings
(`taxonomy.py`), extending packs rather than creating new ones — the brief's
nine packs (declarations, expressions, conversions, pointers,
initialization, storage duration, preprocessor, control flow, linkage) were
already established in Phase 3/4:

| Pack | New in Phase 5 | Total implemented |
|---|---|---|
| Declarations | 5.2, 5.3, 2.7 | 6 |
| Expressions | 13.1, 13.6 | 6 |
| Conversions | 7.4, 11.1, 11.6 | 8 |
| Pointers | 18.3, 18.4, 19.1 | 6 |
| Control flow | 16.2, 16.5, 17.4, 15.4, (2.1 retrofit) | 11 |
| Linkage | 5.8, 5.9, 8.5, 8.8 | 8 |
| Preprocessor | 2.5, 5.4, 21.2 | 6 |
| Initialization / Storage duration / Essential types | — (no new rules this phase) | 8 |

## 6. Industrial Validation

`rule-engine/tests/conformance/embedded_corpora.py` (Phase 4's 8-function
corpus) was expanded with **4 new functions specifically targeting Phase 5
rule packs** — one per codebase, chosen to exercise a construct that
genuinely appears in that codebase's idioms:

| Corpus | New function | Idiom / rule pack exercised |
|---|---|---|
| STM32 HAL | `HAL_UART_GetState` | status-register `switch` decoder — Rule 16.2/16.4/16.5 (well-formed switch), plus a locally-shadowed scratch variable (Rule 5.3) |
| CMSIS | `NVIC_SetPriorityChecked` | pointer-into-array-object bounds check before a priority write (Rule 18.3) |
| FreeRTOS | `vTaskDelete` | list-walk with a single `goto` to a shared cleanup label (Rule 15.4 compliance case) + one ABI-only unused parameter (Rule 2.7) |
| lwIP | `pbuf_copy` | `memcpy` between two pointers both derived from the same shared buffer — a real Rule 19.1 aliasing hazard |

**Result (`rule-engine/tests/conformance/embedded_corpus_report.json`,
12 functions × 59 rules = 708 rule/function pairs):**

- **Crashes: 0/708.**
- **14 real findings**, including genuine new-rule detections proving the
  Phase 5 rules work on realistic code, not just synthetic conformance
  vectors: Rule 5.3 fires on `HAL_UART_GetState`'s shadowed scratch
  variable, Rule 2.7 fires on `vTaskDelete`'s unused `xIndex` parameter,
  Rule 19.1 fires on `pbuf_copy`'s aliased-buffer `memcpy`, Rule 2.1 fires
  (correctly) on a `break` statement made unreachable by an immediately
  preceding `return` inside one switch case, Rule 15.1 fires on the
  `goto` usage in `vTaskDelete` (advisory — "goto should not be used" — even
  though the *pattern* it's used in is the single-goto-per-loop-exit case
  Rule 15.4 explicitly permits).
- **9 corpus-construction artifacts** (all Rule 8.4 — "compatible
  declaration visible" — firing because every corpus unit is a standalone
  TU with no separate header prototype; a gap in the corpus, not a real
  cross-TU issue), separated from findings in the report as before.
- **5 documented unsupported constructs** (unchanged from Phase 4 — macro
  pre-expansion bodies, bit-fields, inline assembly, volatile-qualifier
  propagation through member chains, designated initializers).

## 7. Deliverables

**Implemented rule count: 59** (37 carried over from Phases 1–4 + 22 new
Phase 5 rules). `RuleRegistry.list_rule_ids()` / `GET
/api/v1/rules/catalog` reflect this live.

**Disabled rules: 0.** Every registered rule has at least a `positive`/
`negative` conformance pair (`rule_enablement.json`:
`"disabled_count": 0`).

**Experimental rules: 0.** No rule fell below the confidence thresholds
(`rule_enablement.json`: `"experimental_count": 0`). 36 rules are flagged
`legacy_partial_conformance` (enabled, but missing `macro`/`embedded`/`edge`
cases — a tracked backlog, not a quality problem today).

**Precision estimates:** 100% average precision, 100% average recall, 0%
average false-positive rate across all 59 rules / 187 conformance cases
(`tests/conformance/conformance_report.json`).

**False positive report:** see §6 — 0 crashes across 708 rule/function
pairs against STM32 HAL/CMSIS/FreeRTOS/lwIP-modeled code; 14 real findings
(reviewed and expected, several specifically validating new Phase 5 rules);
9 corpus-construction artifacts explicitly excluded from the finding count.

**Benchmark report**
(`rule-engine/tests/performance/performance_report.json`, regenerated
against the full 59-rule set):

```json
{
  "baseline": { "loc": 18000, "functions": 1200, "duration_ms": 505.2 },
  "measured_ms_per_loc": 0.0281,
  "projections": {
    "100k_loc_projected_seconds": 2.81,  "100k_loc_meets_target": true,
    "500k_loc_projected_seconds": 14.03, "500k_loc_meets_target": true
  },
  "incremental": { "fraction_of_baseline": 0.0796, "meets_target": true }
}
```

Both targets are met with wide margin even with 59 rules (up from 37) —
adding 22 mostly-AST/type-system rules had negligible throughput impact
compared to the CFG/dataflow-heavy rules already in the Phase 4 baseline.
Same rule-engine-only caveat as Phases 3–4 applies: excludes real
`clang-worker` parse time.

**Coverage roadmap** (`rule_capability_matrix.py` / `GET
/api/v1/rules/catalog/roadmap`, 158 total cataloged rules):

| Tier | Phase 4 | Phase 5 |
|---|---|---|
| `implemented` | 37 | **59** |
| `ready_now` | 95 | **73** |
| `blocked_on_ast_metadata` | 21 | 21 |
| `blocked_on_process` | 5 | 5 |

(The `ready_now` drop from 95→73 is exactly the 22 rules that moved to
`implemented` — the roadmap is a closed accounting, not an estimate. Note
this also fixed a latent bug: `coverage_matrix.py`'s static `_RAW` table
still had `"Planned: reuse ..."` unsupported-reasons for 22 rules that were
already registered, so the roadmap was reporting `implemented: 37` even
though the registry had 59 rules loaded. All 22 entries' reasons are now
cleared to `None`.)

## Verification

```bash
cd rule-engine && python -m pytest -q                     # 88 tests (was 86 in Phase 4)
cd rule-engine && python -m ruff check src tests
cd backend && python -m pytest -q                          # 22 tests
cd backend && python -m ruff check src tests

# Regenerate the Phase 5 reports:
python -m pytest tests/conformance -q                                    # conformance_report.json, rule_enablement.json, analyzer_reuse.json
python -m pytest tests/conformance/test_embedded_corpora.py -q           # embedded_corpus_report.json
python -m pytest tests/performance -q                                    # performance_report.json
```
