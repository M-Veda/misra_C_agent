# Phase 7 — Clang-Worker Metadata Gap Elimination

Phase 6 completed all `ready_now` rule batches (132 rules, 83.5% coverage).
Phase 7 extends **clang-worker metadata extraction** to eliminate
`blocked_on_ast_metadata` rules — **no new rule implementations** in this phase.

## 1. Metadata Gap Analysis

Generated `rule-engine/reports/metadata_gap_report.json` via
`metadata_gap_analysis.py`.

| Metric | Value |
|---|---|
| **Blocked rules analyzed** | **21** |
| **Gaps fully resolved** | **20** |
| **Gaps partially resolved** | **1** (Rule 4.2 — trigraphs need raw source scan) |
| **Projected newly unblocked** | **20** |
| **AST schema version** | **2 → 3** |

### Gap categories addressed

| Category | Rules | Example fields |
|---|---|---|
| **AST / literals** | 4.1, 7.1–7.3 | `raw_literal_spelling`, `literal_base`, suffix flags |
| **Bit-fields** | 6.1, 6.2 | `is_bit_field`, `bit_field_width`, signedness |
| **Arrays / VLA** | 8.11, 18.8 | `array_size_expression`, `is_variable_length_array` |
| **Enums** | 8.12 | `enumerator_value`, `is_implicit_enumerator` |
| **Initializers** | 9.2, 9.4 | `is_fully_bracketed`, `duplicate_designator` |
| **Types / casts** | 11.2, 18.5 | `is_incomplete`, `pointer_nesting_depth` |
| **Expressions** | 12.1, 12.5 | `precedence_level`, `sizeof_operand_is_decayed_array` |
| **Calls** | 17.5, 21.13, 22.4 | `call_argument_shapes`, `fopen_mode` |
| **Preprocessor** | 20.5, 20.10 | `undef_directives`, `body_tokens`, `#`/`##` flags |

## 2. AST Serialization Extensions (`ast_serializer.cpp` v3)

Extended `TypeInformation` (7 new fields):

- `is_incomplete`, `pointer_nesting_depth`
- `is_variable_length_array`, `array_size`, `array_size_expression`
- `array_size_is_constant`, `is_parameter_decayed_array`

Extended `semantic_properties` on:

- Literals (raw spelling, suffixes, escape termination)
- Declarations (storage class, linkage, bit-fields, enumerators)
- Expressions (precedence, side-effects, volatile access, value category)
- Calls (`fopen` mode, argument shapes, ctype range hints)
- Casts (incomplete-type conversion flags)

## 3. PPCallbacks Extension (`preprocessor_tracker.cpp`)

| Capture | Message | Unblocks |
|---|---|---|
| `#undef` | `UndefDirective` | Rule 20.5 |
| `#pragma` | `PragmaDirective` | Pragma-aware rules |
| Macro body tokens | `MacroBodyToken[]` | Rule 20.10 |
| `#` / `##` detection | `uses_stringify`, `uses_token_paste` | Rule 20.10 |

## 4. Validation (132 existing rules)

| Check | Result |
|---|---|
| **Pytest** | **110 passed** (+4 Phase 7 tests) |
| **Conformance precision** | **No regression** — all 132 suites unchanged |
| **Benchmark (18K LOC)** | **878 ms** — within noise band of Phase 6.5 |
| **Cache hit rate** | **77.4%** — no regression |
| **Cache budgets** | **0 violations** |
| **Analyzer reuse** | **100%** |

Phase 7 intentionally does **not** register new rules; tier reclassification
happens when Phase 7.1 implements the 20 newly unblocked rules.

## 5. Serialization Growth

| Dimension | Estimate |
|---|---|
| **Schema version** | 2 → 3 |
| **New proto messages** | `UndefDirective`, `PragmaDirective`, `MacroBodyToken` |
| **TypeInformation fields** | +7 per typed node |
| **semantic_properties** | +4–8 keys per literal/decl/call |
| **Preprocessor payload** | +15–40% average TU size |

## 6. Remaining Blockers After Phase 7

| Tier | Count | Notes |
|---|---|---|
| `blocked_on_ast_metadata` | **1** | Rule 4.2 (trigraph raw-source scan) |
| `blocked_on_process` | **5** | Process/documentation rules |
| `ready_now` (projected) | **20** | Awaiting Phase 7.1 rule implementation |

## 7. Verification

```bash
cd rule-engine && python -m pytest -q
cd rule-engine && python -m pytest tests/test_metadata_gap_analysis.py -q
python -c "from misra_platform_rules.metadata_gap_analysis import write_metadata_gap_report; write_metadata_gap_report('reports')"
```

Regenerate protobuf stubs after proto change:

```bash
# From repo root — regenerate Python + C++ stubs from shared/contracts/clang_analysis.proto
```
