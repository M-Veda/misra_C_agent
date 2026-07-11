# Phase 3 — Industrial-Scale MISRA C:2012 Coverage

Phase 3 scales the rule engine from 5 hand-written pilot rules to a
taxonomy-driven, infrastructure-reuse architecture covering the full MISRA
C:2012 rule set, explicitly designed so MISRA C:2023 can be added as a new
`standards/misra_c_2023/` package without touching the shared analyzers,
the dispatcher, or the review platform.

**No rule quality was traded for rule count.** Every implemented rule ships
with a conformance suite (positive + negative cases, several with edge/macro
cases too) and is verified at precision = recall = 1.0 against that suite
before being counted as "implemented." Rules that would need AST/semantic
data the current `clang-worker` pipeline doesn't emit yet are left
**unimplemented and explicitly labeled**, not stubbed out with a fake
detector — see [Unsupported Rules](#unsupported-rules--known-limitations) below.

## 1. Rule Taxonomy

Every rule is classified along two independent axes (`rule-engine/src/misra_platform_rules/taxonomy.py`):

| Category | Meaning | Example rules (implemented) |
|---|---|---|
| **A** — AST-only | Detectable from raw AST node kind/shape alone | 12.3 (comma operator), 15.1 (`goto`), 13.4 (assignment result used) |
| **B** — Type-system | Needs essential-type/cast/qualifier info | 10.1–10.7 (essential types), 11.4/11.5/11.9 (pointer conversions), 8.14 (`restrict`) |
| **C** — Control-flow | Needs a CFG view of a function body | 15.6 (compound-statement bodies), 16.3/16.4/16.6 (switch structure) |
| **D** — Data-flow | Needs def/use tracking across statements | 9.1 (uninitialized read), 2.2 (dead store) |
| **E** — Cross-translation-unit | Needs facts from >1 TU | 5.1 (external-id distinctness), 8.4/8.6/8.7/8.10 (linkage) |
| **F** — Preprocessor | Needs macro-table/conditional-compilation metadata | 20.4/20.7/20.14, 21.1 |
| **G** — Configuration/build-system | Needs toolchain/build config, not source | Dir 1.1–1.4, 3.1/3.2 (documentation-only) |

`RuleMetadata` (in `rule-engine/src/misra_platform_rules/rule_result.py`) carries
this classification plus the dependency-graph fields for every rule:
`implementation_category`, `rule_pack`, `requires_type_info`, `requires_cfg`,
`requires_dataflow`, `requires_linkage`, `requires_macro_expansion`,
`rule_dependencies`.

### Coverage matrix

`rule-engine/src/misra_platform_rules/coverage_matrix.py` catalogs **every**
MISRA C:2012 directive and rule (175 entries: 17 directives + 158 rules)
with its category, rule pack, MISRA classification (mandatory/required/advisory),
and — for anything not yet implemented — a specific `unsupported_reason`
(e.g. *"Requires raw token/comment stream, not in AST"* for 3.1/3.2, or
*"Planned: reuse CFGBuilder.unreachable_statements"* for 2.1).

Served live at:
- `GET /api/v1/rules/catalog/coverage-matrix` — full matrix + summary counts
- `GET /api/v1/rules/catalog/coverage` — simpler by-standard/by-category summary
- `GET /api/v1/rules/catalog` — implemented-rule metadata (now including all
  taxonomy fields above)

Current totals (also in [Deliverables](#8-deliverables)):

| | Count |
|---|---|
| Total directives cataloged | 17 |
| Total rules cataloged | 158 |
| **Implemented rules** | **36** |
| Unimplemented rules (labeled, not stubbed) | 122 |
| Category A (AST-only) | 52 |
| Category B (type-system) | 44 |
| Category C (control-flow) | 9 |
| Category D (data-flow) | 23 |
| Category E (cross-TU) | 7 |
| Category F (preprocessor) | 27 |
| Category G (config/build) | 13 |

## 2. Rule Dependency Graph → Execution Groups

`rule-engine/src/misra_platform_rules/execution_planner.py` adds
`resolve_execution_groups(rules)`, which turns each rule's declared
`implementation_category` (via `taxonomy.CATEGORY_EXECUTION_ORDER`) and
`rule_dependencies` into an ordered list of **waves**: every rule inside a
wave can run fully in parallel; a wave must finish before the next starts.
This guarantees:

- Cheap, purely-structural category A/F rules run first.
- Category B (type-system) rules run once type/cast/qualifier data is
  conceptually available.
- Category C/D (control-flow/data-flow) run next, since they build a
  heavier per-function CFG/dataflow pass.
- Category E/G (cross-TU, build-config) run last, since they need
  project-wide state (`LinkageIndex`) rather than a single TU's AST.
- Any rule that explicitly declares a `rule_dependencies` entry is
  guaranteed to run strictly after that dependency (topological sort with
  cycle detection — `CyclicRuleDependencyError`).

`RuleExecutionEngine.execute(context, rules, grouped=True)` can opt into
staged execution; it defaults to `grouped=False` (single wave) because no
shipped rule currently reads another rule's output, so today the two modes
produce identical results — the staged mode exists so future rules that
*do* need ordering (e.g. a rule that should only fire when a stricter
sibling rule didn't already flag the same node) have a mechanism to declare
that without changing the dispatcher.

Tests: `rule-engine/tests/test_execution_planner.py` (category ordering,
explicit dependency ordering, cycle detection, and a check that running the
resolver over the real 36-rule registry accounts for every rule exactly once).

## 3. Shared Analysis Infrastructure

Ten reusable analyzers (`rule-engine/src/misra_platform_rules/analyzers/`),
exposed as cached properties on `BaseRulePlugin` (`self.essential_types()`,
`self.casts()`, etc.) so rules never duplicate this logic:

| Analyzer | Backs rule pack | Responsibility |
|---|---|---|
| `EssentialTypeAnalyzer` | Essential Types | Essential-type ranking/category, narrowing, inappropriate operand pairs |
| `CastAnalyzer` | Conversions | Explicit/implicit cast detection, qualifier loss, narrowing, pointer-type changes |
| `PointerAnalyzer` | Pointers | Pointer/null detection, pointer arithmetic, incompatible pointer assignment, escaping addresses |
| `QualifierAnalyzer` | (shared) | const/volatile/restrict tracking, qualifier loss on assignment |
| `CFGBuilder` | Control Flow | Exit points, unreachable statements, nesting depth, switch-fallthrough |
| `DataFlowEngine` | Initialization | Uninitialized reads, dead stores (best-effort intra-procedural) |
| `SymbolIndex` | Declarations / Storage Duration | Declaration indexing, duplicate/shadowing names, storage class, linkage |
| `LinkageIndex` | Linkage | Project-wide (cross-TU) symbol occurrences, multiple-definition and incompatible-type-spelling detection |
| `MacroAnalyzer` | Preprocessor | Macro table analysis, reserved-identifier checks, unparenthesized macro bodies |
| `ExpressionClassifier` | Expressions | Constant-expression/side-effect/condition classification |

Unit tests for all ten: `rule-engine/tests/test_analyzers.py` (13 tests).

## 4. Rule Packs

Ten thematic rule packs (`rule-engine/src/misra_platform_rules/standards/misra_c_2012/rules/rule_pack_*.py`),
each reusing its primary analyzer above:

| Pack | Rules implemented |
|---|---|
| Essential Types | 10.2 |
| Conversions | 10.4, 10.5, 10.7 |
| Declarations | 8.2, 8.6, 8.14 |
| Pointers | 11.4, 11.5, 11.9, 18.2 |
| Control Flow | 15.1, 15.6, 16.3, 16.4, 16.6 |
| Preprocessor | 20.4, 20.7, 20.14, 21.1 |
| Expressions | 12.3, 13.4, 13.5, 14.4 |
| Initialization | 9.1, 2.2 |
| Storage Duration | 8.9, 18.6 |
| Linkage | 5.1, 8.7, 8.10 (+ upgraded 8.4) |

Plus the 5 Phase 1.2 pilot rules (10.1, 10.3, 11.8, 15.5, 8.4 — 8.4 was
upgraded in Phase 3 to add a true cross-TU `LinkageIndex` check). **36 rules
implemented in total.**

## 5. Conformance Harness

`rule-engine/tests/conformance/`:
- `ast_builders.py` — fluent synthetic-AST `Builder` (no hand-written node dicts)
- `fixtures.py` — one `RuleConformanceSuite` per implemented rule (positive +
  negative cases; edge/macro cases added where the rule's failure mode is
  macro-driven, e.g. 20.4/20.7/21.1)
- `conformance.py` (in `src/`) — `ConformanceRunner` computes **precision,
  recall, and false-positive rate** per rule by running each suite's cases
  through the real `detect()` method
- `test_conformance.py` — `test_every_suite_case_matches_expectation` (functional
  correctness) and `test_conformance_report_generation` (writes
  `conformance_report.json` and asserts precision/recall ≥ target thresholds)

**Current result: all 36 implemented rules score precision = 1.0, recall =
1.0, false_positive_rate = 0.0** against their conformance suites
(`rule-engine/tests/conformance/conformance_report.json`). This reflects the
hand-authored positive/negative/edge test cases available today; it is not
a claim about false-positive rates on arbitrary real-world code, which
would require a much larger embedded-specific corpus (see [Known Accuracy
Limitations](#known-accuracy-limitations)).

## 6. Performance Targets

| Target | Budget |
|---|---|
| 100K LOC project | < 10 minutes |
| 500K LOC project | < 30 minutes |
| Incremental (changed subset) | < 25% of a full run |

**Environment caveat:** this sandboxed dev environment has no real
100K/500K-LOC embedded C corpus and no running `clang-worker` AST pipeline
to parse one. `rule-engine/tests/performance/` therefore benchmarks the
**rule-engine execution layer only** (dispatch + all 36 rules + shared
analyzers + `LinkageIndex` cross-TU build) against a synthetic AST project
generator (`synthetic_project.py`, ~15 lines / ~18 AST nodes per function,
structurally representative of embedded C: locals, casts, conditionals,
switches, calls), then linearly extrapolates measured ms/LOC to the target
sizes. `benchmark_rule_engine.py` is runnable standalone or via
`test_performance.py`, and always regenerates `performance_report.json`.

Latest measured run (30 TUs × 40 functions = 18,000 LOC synthetic baseline):

```json
{
  "baseline": { "loc": 18000, "functions": 1200, "duration_ms": 288.4 },
  "measured_ms_per_loc": 0.016,
  "projections": {
    "100k_loc_projected_seconds": 1.6,   "100k_loc_meets_target": true,
    "500k_loc_projected_seconds": 8.01,  "500k_loc_meets_target": true
  },
  "incremental": {
    "loc": 1800, "fraction_of_baseline": 0.098, "meets_target": true
  }
}
```

This is a **rule-engine-only lower bound**, not an end-to-end SLA — a real
run's wall-clock time will be dominated by `clang-worker` parsing (libclang
invocation per TU) and network/IPC to it, neither of which is modeled here.
The existing `tools/benchmark-harness/benchmark_ast_pipeline.py` measures
that AST-parsing side separately (against a real `compile_commands.json`
project) but requires a live `clang-worker`, which isn't running in this
environment. Once both numbers are available for a real project, end-to-end
time = AST-parsing time + rule-engine time (the two pipeline stages already
run per-TU in `WorkerPool`, so they compose additively per TU and overlap
across TUs up to `tu_workers` concurrency).

## 7. Metrics

`backend/src/misra_platform/services/rule_dispatcher.py` (per analysis run,
persisted into `RuleRunStatisticsRecord.metrics_json`):
- `per_rule` timing/violation-count/success (existing, Phase 1)
- `rule_timing_summary` — total/avg/max ms + invocation count per rule *for this run*
- `confidence_distribution` — violation counts bucketed into 0.0–0.2 … 0.8–1.0
- `false_positive_candidates` — count of violations with confidence < 0.6

`backend/src/misra_platform/services/metrics_service.py` (project/rule-wide,
computed on demand since they span every run and every review ever recorded):
- `confidence_distribution(project_id?, rule_id?)` — same bucketing, across
  all persisted violations, overall and per-rule
- `review_acceptance_rate(rule_id?)` — accept+edit ÷ (accept+edit+reject+false_positive+suppress),
  overall and per-rule, plus raw action counts
- `rule_timing_summary()` — avg/max/invocations per rule across every
  `RuleExecutionMetricRecord` ever written

Exposed via `backend/src/misra_platform/api/v1/metrics.py`:
- `GET /api/v1/metrics/confidence-distribution?project_id=&rule_id=`
- `GET /api/v1/metrics/review-acceptance-rate?rule_id=`
- `GET /api/v1/metrics/rule-timing-summary`

## 8. Deliverables

**Implemented rule count: 36** (5 Phase 1.2 pilot rules + 31 new Phase 3 rules
across 10 rule packs). Full list in `rule-engine/src/misra_platform_rules/standards/misra_c_2012/manifest.yaml`.

**Coverage matrix:** 175 cataloged entries (17 directives + 158 rules), 36
implemented / 122 unimplemented-and-labeled. Live at `GET
/api/v1/rules/catalog/coverage-matrix`; raw data in `coverage_matrix.py`.

**Benchmark numbers:** see [Performance Targets](#6-performance-targets) —
synthetic-AST rule-engine throughput of ~0.016 ms/LOC, projecting well under
both the 100K LOC (<10 min) and 500K LOC (<30 min) budgets, with incremental
runs at ~10% of full-run time (well under the 25% budget). These are
rule-engine-only figures; see the caveat above about missing real-corpus /
live-`clang-worker` measurements in this environment.

### Unsupported rules & known limitations

122 of 158 MISRA C:2012 rules are not yet implemented. They fall into four groups:

1. **Genuinely out of AST-analysis scope** (Category G, ~13 rules): Dir 1.1–1.4,
   3.1, 3.2 — these require compiler-diagnostic configuration, documented
   language-extension usage, or raw token/comment streams, not a semantic AST.
2. **Blocked on `clang-worker` AST schema gaps** (~30 rules): need data the
   current AST serialization doesn't emit yet — raw literal spelling (4.1,
   7.1–7.3), bit-field width metadata (6.1, 6.2), enumerator values (8.12),
   designated-initializer metadata (9.4), macro-body raw tokens (20.10), etc.
   Each is labeled with the specific missing field in `coverage_matrix.py`.
3. **Need a capability not yet built on top of existing analyzers** (~25
   rules): whole-program call graphs (17.2), constant-folding/propagation
   (12.4, 14.3), pointer-aliasing analysis (19.1), buffer-size/alloc-free
   dataflow (21.17/21.18, 22.1/22.6) — these are dataflow-hard problems
   beyond the current best-effort intra-procedural `DataFlowEngine`.
4. **Straightforward reuse of existing analyzers, simply not yet written**
   (~55 rules, the majority): e.g. 2.1 (`CFGBuilder.unreachable_statements`
   already computes this), 5.2/5.3 (`SymbolIndex.duplicate_names_within` /
   `.shadowing_pairs`), 11.1/11.3/11.6 (`CastAnalyzer`), 13.1/13.3/13.6
   (`ExpressionClassifier`), 21.2/21.3/21.6-21.8 (`MacroAnalyzer`/CallExpr
   name-matching). These are the highest-ROI next batch — the shared
   infrastructure already has the primitive each of them needs.

### Known accuracy limitations

- Conformance precision/recall/FPR = 1.0 for all 36 rules is measured
  against **hand-authored** synthetic positive/negative/edge cases (2+ per
  rule, more for macro-sensitive rules), not a large real-world corpus.
  Real embedded C will exercise AST shapes the fixtures don't cover yet.
- `DataFlowEngine` (rules 9.1, 2.2) is intra-procedural and best-effort: it
  does not follow pointers, does not model `goto`/`longjmp` control transfer
  precisely, and does not do interprocedural analysis — a variable
  initialized by a called function's out-parameter, for instance, may be
  misflagged as an uninitialized read.
- `CFGBuilder` (rules 15.6, 16.3, 16.4, 16.6) approximates control flow
  structurally from the AST rather than building a true basic-block CFG; it
  handles the common `if/while/for/do/switch` shapes tested in the
  conformance suite but not every legal C control structure.
- `LinkageIndex` (cross-TU rules 5.1, 8.4, 8.6, 8.7, 8.10) is built once
  per analysis run from every TU's AST in memory; it has not been validated
  against a 500K-LOC multi-TU project, only synthetic multi-TU fixtures.
- Confidence scores feed `false_positive_candidates` (<0.6 threshold) but
  that threshold is a heuristic, not calibrated against labeled real-world
  false positives yet — `review_acceptance_rate` (Section 7) is the metric
  intended to calibrate it over time as engineers actually review violations.

## Verification

```bash
cd rule-engine && python -m pytest -q                     # 22 tests (analyzers, rule packs, planner, conformance, perf)
cd rule-engine && python -m ruff check src tests
cd backend && python -m pytest -q                         # 16 tests (incl. coverage-matrix + metrics endpoints)
cd backend && python -m ruff check src tests
python rule-engine/tests/performance/benchmark_rule_engine.py   # regenerate performance_report.json standalone
```
