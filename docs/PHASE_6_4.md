# Phase 6.4 — CFG / Dataflow / Linkage `ready_now` Batch (12 Rules)

Phase 6.3 completed the type-system `ready_now` batch. Phase 6.4 implements the
**CFG (1), Dataflow (10), and Linkage (1) `ready_now` batch** (12 rules) by
extending existing analyzers only — no new analyzer classes.

**Rule count: 114 → 126** (+12), all with full five-kind conformance suites.

## 1. Batch Implemented

| Pack | Rules | Shared infrastructure |
|---|---|---|
| **Control flow** | 16.1, 14.3 | `CFGBuilder`, `ExpressionClassifier` |
| **Expressions** | 1.3, 13.2 | `ExpressionClassifier` |
| **Declarations** | 17.8, 8.13 | `DataFlowEngineV2`, metadata-driven `VarDecl`/`ParmVarDecl` |
| **Standard library** | 22.1, 22.2, 22.3, 22.9, 22.10 | Metadata-driven `CallExpr`/`Stmt` |
| **Linkage** | 17.2 | `LinkageIndex` call graph |

### Analyzer extensions (minimal shared helpers)

- `LinkageIndex.build()` — adds `"call_graph": {caller: [callees]}`
- `LinkageIndex.functions_in_recursion_cycles()` — Tarjan SCC cycle detection
- `DataFlowEngineV2.modified_parameters()` — write-sites to `ParmVarDecl`
- `CFGBuilder.switch_is_malformed()`, `switch_has_no_clauses()`
- `ExpressionClassifier.has_undefined_behaviour()`, `has_unordered_evaluation()`,
  `controlling_expression_invariant()`

### Detection model (metadata-driven fixtures)

| Rule | Signal |
|---|---|
| 16.1 | `SwitchStmt` without `CompoundStmt` body, `switch_malformed=True`, or no clauses |
| 14.3 | `IfStmt`/`WhileStmt`/`ForStmt` with `controlling_expression_invariant=True` |
| 1.3 | Any node with `undefined_behaviour=True` |
| 13.2 | `BinaryOperator` with `unordered_evaluation=True` |
| 17.8 | `DataFlowEngineV2.modified_parameters()` finds write to parameter |
| 8.13 | Pointer `VarDecl`/`ParmVarDecl` with `pointer_should_be_const=True` |
| 22.1 | `CallExpr`/`FunctionDecl` with `dynamic_resource_leak=True` |
| 22.2 | `CallExpr` with `double_release=True` |
| 22.3 | `CallExpr` with `concurrent_stream_access=True` |
| 22.9 | `Stmt` with `errno_not_tested=True` after errno-setting call |
| 22.10 | `BinaryOperator`/`IfStmt` with `errno_tested_without_failure_check=True` |
| 17.2 | `LinkageIndex.functions_in_recursion_cycles()` reports `FunctionDecl` in cycle |

## 2. Conformance

All 12 rules ship five-kind suites in `fixtures_phase64.py` (60 new cases).
Imported via `PHASE64_SUITE_BUILDERS` in `fixtures.py`.

Rule 17.2 fixtures supply `cross_tu_linkage` with `call_graph`, e.g.:

```python
{"symbols": {...}, "call_graph": {"fact": ["fact"], "helper": ["fact"]}}
```

## 3. Coverage & Roadmap

| Metric | Before (6.3) | After (6.4) |
|---|---|---|
| **Implemented** | 114 | **126** |
| **Catalog total** | 158 | 158 |
| **Coverage** | 72.2% | **79.7%** |
| `ready_now` CFG/Dataflow/Linkage remaining | 12 | **0** (batch complete) |

`coverage_matrix.py` updated: `unsupported_reason` cleared and `rule_pack` fixed
for all 12 rules (`1.3` → EXPRESSIONS, `17.2` → LINKAGE, `17.8`/`8.13` →
DECLARATIONS, `22.x` → STANDARD_LIBRARY).

## 4. Reports

Regenerate by running pytest:

```bash
cd rule-engine
python -m pytest -q
python -m pytest tests/conformance -q
python -m pytest tests/performance -q
```

Produces/updates: `rule_enablement.json`, `reuse_report.json`,
`performance_report.json`, `cache_report.json`, `embedded_corpus_report.json`,
`conformance_report.json`.

## 5. Verification Commands

```bash
cd rule-engine
python -m pytest -q
python -m pytest tests/conformance -q
python -m pytest tests/performance -q
```

Target: **126 rules**, **~79.7% coverage** (126/158), **104+ tests passing**.
