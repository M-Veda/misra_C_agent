# Phase 6.5 — Alias-Analysis `ready_now` Batch (6 Rules)

Phase 6.4 completed the CFG / dataflow / linkage `ready_now` batches. Phase 6.5
implements the final **`ready_now` alias-analysis batch** (6 rules) using
`AliasAnalyzer` exclusively — no new analyzer classes.

**Rule count: 126 → 132** (+6), all with full five-kind conformance suites.

## 1. Batch Implemented

| Pack | Rules | Shared infrastructure |
|---|---|---|
| **Pointers** | 18.1 | `AliasAnalyzer.pointer_arithmetic_violations()` |
| **Standard library** | 21.15, 21.17, 21.18, 21.20, 22.6 | `AliasAnalyzer` mem/string/FILE queries |

### Analyzer extensions (minimal shared helpers on `AliasAnalyzer`)

- `pointer_arithmetic_violations()` — out-of-bounds pointer arithmetic
- `incompatible_mem_calls()` — memcpy/memmove/memcmp type compatibility
- `string_buffer_overflow_calls()` — strcpy/strcat overflow signals
- `size_exceeds_destination_calls()` — size argument vs destination
- `use_after_string_invalidation_reads()` — strtok/asctime invalidation
- `use_after_file_close_reads()` — FILE* use after `fclose`
- `unsupported_patterns()` — shapes the analyzer cannot model precisely

All six rules call `self.aliases(function_node, graph, context)` per function,
matching the Rule 19.1 pattern.

## 2. Conformance

60 new cases in `fixtures_phase65.py` (6 rules × 5 kinds), imported via
`PHASE65_SUITE_BUILDERS`.

| Metric | Before (6.4) | After (6.5) |
|---|---|---|
| Fully conformant (enabled) | 90 | **96** |
| Experimental (legacy partial) | 36 | 36 |
| Disabled | 0 | 0 |

## 3. Coverage & Roadmap

| Metric | Value |
|---|---|
| **Implemented** | **132** |
| **Catalog total** | 158 |
| **Coverage** | **83.5%** |
| `ready_now` remaining | **0** (all mechanical batches complete) |
| `blocked_on_ast_metadata` | **21** |
| `blocked_on_process` | **5** |

## 4. Alias-Analysis Statistics

New module `alias_analysis_statistics.py` generates:

- `alias_analysis_statistics.json` — may-alias pairs, violation signals
- `unsupported_alias_patterns.json` — documented precision limits

Wired into `tests/test_alias_analysis_statistics.py`.

### Unsupported alias patterns (documented)

| Pattern | Meaning |
|---|---|
| `heap_allocation_opaque_target` | malloc/calloc/realloc targets are unknown |
| `pointer_arithmetic_unknown_pointee` | arithmetic on unknown-origin pointers |
| `parameter_pointer_unknown_target` | pointer parameters seeded as unknown |
| `flow_insensitive_points_to` | may-alias is whole-function, not per-point |
| `no_interprocedural_alias` | callee pointer effects not summarized |

## 5. Benchmark & Cache

| Metric | 126 rules (6.4) | 132 rules (6.5) |
|---|---|---|
| Duration (18K LOC / 30 TUs) | 730 ms | **878 ms** (+20%) |
| Cache hit rate | 59.2% | **77.4%** |
| Analyzer reuse | 100% | **100%** |
| Cache budget violations | 0 | **0** |

**Top expensive new rules** (30-TU totals):

| Rule | Total ms | Notes |
|---|---|---|
| 18.1 | ~24 | per-function alias + pointer-arithmetic scan |
| 22.6 | ~18 | FILE invalidation tracking |
| 21.15 | ~15 | mem-call compatibility |

## 6. Verification

```bash
cd rule-engine && python -m pytest -q                     # 106 passed
cd rule-engine && python -m pytest tests/conformance -q
cd rule-engine && python -m pytest tests/performance -q
python -m pytest tests/test_alias_analysis_statistics.py -q
```
