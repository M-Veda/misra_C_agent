# Phase 6.3 — Type-System `ready_now` Batch (14 Rules)

Phase 6.2 completed the AST-only `ready_now` batch. Phase 6.3 implements the
**type-system `ready_now` batch** (14 rules) by extending existing analyzers only
— no new analyzer classes.

**Rule count: 100 → 114** (+14), all with full five-kind conformance suites.

## 1. Batch Implemented

| Pack | Rules | Shared infrastructure |
|---|---|---|
| **Conversions** | 10.6, 10.8 | `EssentialTypeAnalyzer`, `CastAnalyzer` |
| **Pointers** | 11.3, 11.7 | `CastAnalyzer`, `PointerAnalyzer` |
| **Expressions** | 12.2, 12.4 | `ExpressionClassifier` |
| **Control flow** | 14.1, 16.7 | `ExpressionClassifier` |
| **Standard library** | 21.14, 21.16, 21.19, 22.5, 22.7 | `PointerAnalyzer`, metadata-driven `CallExpr` |
| **Declarations** | 8.3 | `SymbolIndex` (not TypedefResolver/TypeSystem) |

### Analyzer extensions (minimal shared helpers)

- `EssentialTypeAnalyzer.is_wider()`
- `CastAnalyzer.is_composite_expression()`, `changes_object_pointer_type()`,
  `casts_pointer_to_non_integer_arithmetic()`, `changes_to_wider_category()`
- `ExpressionClassifier.shift_amount_out_of_range()`, `wraps_on_constant_unsigned()`,
  `loop_counter_is_floating()`, `switch_condition_is_boolean()`
- `PointerAnalyzer.is_file_pointer()`
- `SymbolIndex.incompatible_declaration_groups()` for Rule 8.3

### Detection model (metadata-driven fixtures)

| Rule | Signal |
|---|---|
| 10.6 | `BinaryOperator '='`, rhs `is_composite_expression=True`, rhs rank > lhs |
| 10.8 | `CStyleCastExpr`, composite operand, cast widens essential category, used as operand |
| 11.3 | `CastAnalyzer.changes_object_pointer_type()` between non-void object types |
| 11.7 | Pointer operand cast to floating essential type on target |
| 12.2 | Shift `<<`/`>>`, `shift_amount` ∉ [0, `shift_width`-1] |
| 12.4 | `wraps_on_evaluation=True` on constant unsigned expression |
| 14.1 | `ForStmt` / init `VarDecl` with floating `loop_counter_essential_type` |
| 16.7 | `SwitchStmt` condition child `essential_type == boolean` |
| 21.14 | `memcmp` with `compares_null_terminated_strings=True` |
| 21.16 | `memcmp` arg with `invalid_pointer_argument=True` |
| 21.19 | `returned_pointer_missing_const=True` on `DeclRefExpr`/`UnaryOperator` |
| 22.5 | `UnaryOperator *` on `FILE` pointer (`pointee_type` or spelling) |
| 22.7 | `BinaryOperator` with `eof_operand_modified=True` |
| 8.3 | `SymbolIndex`: same name, `declaration_incompatible=True` |

## 2. Conformance

All 14 rules ship five-kind suites in `fixtures_phase63.py` (70 new cases).
Imported via `PHASE63_SUITE_BUILDERS` in `fixtures.py`.

| Metric | Before (6.2) | After (6.3) |
|---|---|---|
| Fully conformant (non-experimental) | 64 | **78** |
| Experimental (legacy partial) | 36 | 36 |
| Disabled | 0 | 0 |

## 3. Coverage & Roadmap

| Metric | Value |
|---|---|
| **Implemented** | **114** |
| **Catalog total** | 158 |
| **Coverage** | **72.2%** |
| `ready_now` type_system remaining | **0** (batch complete) |
| `ready_now` total remaining | **18** |

`coverage_matrix.py` updated: RulePack `STANDARD_LIBRARY` for 21.14, 21.16,
21.19, 22.5, 22.7; `unsupported_reason` cleared for all 14.

## 4. Type-System Statistics

New module `type_system_statistics.py` generates four JSON reports under
`rule-engine/reports/`:

- `type_conversion_statistics.json`
- `essential_type_mismatch_statistics.json`
- `enum_conversion_statistics.json`
- `signedness_conversion_statistics.json`

Wired into `tests/test_type_system_statistics.py` (runs on conformance
artifacts + writes reports).

## 5. Benchmark Notes

Synthetic baseline (18K LOC, 30 TUs) — type-system rules add sub-ms per-TU cost
via existing analyzer reuse (`essential_types()`, `casts()`, `expressions()`,
`pointers()`, `symbols()`). No new semantic-unit budgets introduced.

| Metric | 100 rules (6.2) | 114 rules (6.3) | Notes |
|---|---|---|---|
| Pytest | 102 passed | **104 passed** | +2 statistics tests |
| Analyzer reuse | 100% | **100%** | all 114 rules |
| New analyzer classes | 0 | **0** | constraint met |

Re-run performance suite after merge to refresh `performance_report.json`:
`python -m pytest tests/performance -q`

## 6. Rule 8.3 Note

Rule 8.3 uses `SymbolIndex.incompatible_declaration_groups()` correlating
multiple declarations of the same identifier. There is no `TypedefResolver` or
`TypeSystem` module — clang-worker populates
`semantic_properties.declaration_incompatible` when declarations disagree.

## 7. Verification

```bash
cd rule-engine && python -m pytest -q                     # 104 passed
cd rule-engine && python -m ruff check src tests

# Regenerate type-system reports:
python -m pytest tests/test_type_system_statistics.py -q

# Regenerate conformance + performance reports:
python -m pytest tests/conformance -q
python -m pytest tests/performance -q
```
