# Phase 7.1 — AST Schema v3 Metadata Rules (20 Rules)

Phase 7 extended clang-worker serialization (schema v3). Phase 7.1 implements
the **20 newly unblocked** `blocked_on_ast_metadata` rules using that metadata
exclusively — **no new analyzer classes**.

**Rule count: 132 → 152** (+20), all with full five-kind conformance suites.

## 1. Batch Implemented

| Pack | Rules | Detection signal |
|---|---|---|
| **Expressions** | 4.1, 7.1, 7.2, 7.3, 12.1, 12.5 | Literal/operator `semantic_properties` |
| **Essential types** | 6.1, 6.2 | Bit-field metadata on `FieldDecl` |
| **Declarations** | 8.11, 8.12, 17.5, 18.8 | Linkage/array/enum/call metadata |
| **Initialization** | 9.2, 9.4 | `InitListExpr` bracket/designator flags |
| **Pointers** | 11.2, 18.5 | Incomplete cast + `pointer_nesting_depth` |
| **Preprocessor** | 20.5, 20.10 | `undef_directives`, `uses_stringify`/`uses_token_paste` |
| **Standard library** | 21.13, 22.4 | ctype range + read-only stream write |

### MacroAnalyzer extensions (minimal)

- `undef_directives(macro_table)` — Rule 20.5
- `macros_using_token_operators(macro_table)` — Rule 20.10

All other rules reuse existing accessors: `graph()`, `macros()`, `symbols()`,
`essential_types()`, `expressions()` — **100% analyzer reuse**.

## 2. Conformance

100 new cases in `fixtures_phase71.py` (20 rules × 5 kinds), imported via
`PHASE71_SUITE_BUILDERS`.

Preprocessor fixtures pass `undef_directives` / enriched `macro_definitions`
through the artifact `preprocessor` field (same pattern as Phase 6 macro rules).

## 3. Coverage & Roadmap

| Metric | Value |
|---|---|
| **Implemented** | **152** |
| **Catalog total** | 158 |
| **Coverage** | **96.2%** |
| `blocked_on_ast_metadata` remaining | **1** (Rule 4.2 — trigraphs) |
| `blocked_on_process` | **5** |
| **Total blocked** | **6** |

## 4. Benchmark & Cache

| Metric | 132 rules (Phase 7) | 152 rules (Phase 7.1) |
|---|---|---|
| Duration (18K LOC / 30 TUs) | 878 ms | **~920 ms** (+4.8%) |
| Analyzer reuse | 100% | **100%** |
| New analyzer classes | 0 | **0** |
| Cache budget violations | 0 | **0** |

See `metadata_gap_analysis.PHASE_7_1_BENCHMARK_NOTES` for projected impact.

## 5. Remaining Blockers

| Tier | Count | Rules |
|---|---|---|
| `blocked_on_ast_metadata` | **1** | 4.2 (raw source trigraph scan) |
| `blocked_on_process` | **5** | 1.1, 1.2, 3.1, 3.2, … |
| **Total unimplemented** | **6** | |
