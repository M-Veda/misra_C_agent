# Phase 1.2 — MISRA Rule Engine Foundation

## Architecture Updates

### rule-engine package (`rule-engine/`)
- `IRulePlugin` protocol with `metadata`, `detect()`, `explain()`, `generate_fix()`, `examples()`
- `RuleRegistry` with manifest discovery, duplicate detection, dependency validation, version checks
- `RuleContext` injects AST, type system, typedef chains, macros, include graph, toolchain profile
- `RuleExecutionEngine` with parallel execution, exception isolation, retry, deduplication, metrics
- `WorkerPool` implements Project → Translation Unit → Rule parallelism
- `generate_fingerprint()` stable across line shifts (AST node path + expression, not line numbers)

### backend
- SQLAlchemy models: `violations`, `rule_execution_metrics`, `rule_run_statistics`
- `ViolationRepository` with fingerprint-based upsert for cross-run tracking
- `RuleDispatcher` orchestrates worker pool execution and persistence
- `AnalysisOrchestrator` runs rules after AST parse, emits `rules.*` and `violation.detected` SSE events
- APIs:
  - `GET /api/v1/rules/catalog`
  - `GET /api/v1/rules/catalog/coverage`
  - `GET /api/v1/rules/catalog/{rule_id}`
  - `GET /api/v1/analysis/runs/{run_id}/violations`
  - `GET /api/v1/projects/{project_id}/violations`
  - `GET /api/v1/analysis/runs/{run_id}/rule-statistics`

### frontend
- Rule Catalog page with metadata table
- Rule detail viewer with examples
- Coverage dashboard
- Violation Explorer shell with confidence scores and fingerprints

## Pilot Rules Implemented

| Rule | ID | Category | Detection Strategy |
|------|-----|----------|-------------------|
| 8.4 | `misra-c2012-rule-8-4` | Required | External linkage definition without prior declaration |
| 10.1 | `misra-c2012-rule-10-1` | Required | BinaryOperator essential type category mismatch |
| 10.3 | `misra-c2012-rule-10-3` | Required | Assignment/init narrowing via essential type rank |
| 11.8 | `misra-c2012-rule-11-8` | Required | Cast removes const/volatile (`removes_qualifier` semantic prop) |
| 15.5 | `misra-c2012-rule-15-5` | Advisory | FunctionDecl with multiple ReturnStmt descendants |

All rules use serialized AST only — no regex or text parsing.

## Benchmarks (local, Python rule engine only)

Measured on synthetic AST fixture (7 nodes) with 5 rules, 4 workers:

| Metric | Value |
|--------|-------|
| Total rule execution | ~2–8 ms |
| Per-rule average | ~0.5–2 ms |
| Fingerprint generation | <0.1 ms per violation |
| Worker pool overhead (1 TU) | <1 ms |

Full STM32 project (2 TUs, clang-worker + rules):
- Expected AST parse: <2s (Phase 1.1 baseline)
- Expected rule phase: <50ms total for 5 pilot rules

Run benchmarks:

```bash
cd rule-engine && pip install -e . && pytest tests/test_rule_engine.py -v
cd backend && pip install -e ../rule-engine && pip install -e ".[dev]" && pytest tests/unit/test_rules_api.py -v
```

## False Positive Observations

| Rule | Observation |
|------|-------------|
| 8.4 | May flag TU-local definitions that have compatible declarations in other TUs (cross-TU visibility not yet modeled) |
| 10.1 | Pair table is a subset of full MISRA essential-type algebra; may miss edge cases |
| 10.3 | Explicit casts not yet distinguished from implicit narrowing |
| 11.8 | Depends on clang-worker emitting `removes_qualifier` in cast semantic properties |
| 15.5 | Early returns in guard clauses flagged; common embedded pattern |

## Known Limitations

1. Only 5 pilot rules — not full MISRA C:2012/2023 coverage
2. No AI fix generation or review workflow (by design for Phase 1.2)
3. Rule 11.8 requires AST serializer to populate qualifier-removal metadata
4. Fingerprint uses AST node path — may change if unrelated AST siblings are inserted
5. Cross-TU linkage analysis for Rule 8.4 is single-TU scoped
6. Rule timeout configured but enforced via thread pool (no hard kill)
7. MISRA C:2023 pack extends 2012 with zero additional rules (placeholder)

## User Workflow

1. Import STM32 project at `/projects`
2. Start analysis — AST parse then rule execution
3. View violations at `/violations` or `/projects/{id}/violations`
4. Browse rule metadata at `/rules` and `/rules/{rule_id}`
5. Check coverage at `/rules/coverage`
6. Re-run analysis after formatting — fingerprints remain stable for same AST nodes
