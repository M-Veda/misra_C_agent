# Industrial Validation Runbook

Regenerate all Phase 9 validation reports and verify release acceptance gates.

## Quick Run

```bash
python validation/run_all.py
```

Exit code 0 = all acceptance gates passed.

## Step-by-Step

### 1. Conformance Suite

```bash
cd rule-engine
python -m pytest tests/conformance/test_conformance.py -v
```

Output: `tests/conformance/conformance_report.json`

Verify: all rule suites pass, precision ≥ 0.95 average.

### 2. Embedded Corpus Validation

```bash
python -m pytest tests/conformance/test_embedded_corpora.py -v
```

Output: `tests/conformance/embedded_corpus_report.json`

Verify:
- `crash_count == 0`
- 6 codebases: stm32_hal, cmsis, freertos, lwip, zephyr, mbedtls
- Review `unsupported_constructs` and `corpus_construction_artifacts`

### 3. Performance Benchmark

```bash
python tests/performance/benchmark_rule_engine.py
```

Output: `tests/performance/performance_report.json`

Verify: 100K LOC projection ≤ 600 seconds.

### 4. Review Generated Matrices

```bash
ls validation/reports/
```

| File | Contents |
|------|----------|
| `phase9_validation_summary.json` | Master rollup + acceptance |
| `support_matrix.json` | Precision, FP, rule status |
| `compatibility_matrix.json` | Stack/toolchain matrix |
| `benchmark_report.json` | Performance data |

### 5. Docker Validation (CI parity)

```bash
docker compose -f docker-compose.yml \
  -f infrastructure/compose/docker-compose.validation.yml run validation
```

## Acceptance Gate Reference

See `validation/acceptance_gates.json`:

```json
{
  "embedded_crash_count": { "max": 0 },
  "conformance_avg_precision": { "min": 0.95 },
  "performance_100k_loc_seconds": { "max": 600 },
  "corpora_required": ["stm32_hal", "cmsis", "freertos", "lwip", "zephyr", "mbedtls"]
}
```

## False Positive Classification

| Type | Example | Action |
|------|---------|--------|
| Corpus artifact | Rule 8.4 on standalone TU | Document, do not fix |
| Known embedded pattern | Register cast in HAL | Expected finding, not a bug |
| Engine bug | Wrong rule firing on compliant code | File defect, fix rule |

## When Validation Fails

1. Read `phase9_validation_summary.json` → `acceptance.checks`
2. For crashes: check `embedded_corpus_report.json` → `crashes` for traceback
3. For precision: check `conformance_report.json` for per-rule FP/FN
4. For performance: check `benchmark_report.json` → `projections`

## Archiving for Release

```bash
mkdir -p release-artifacts/v1.0.0-rc1/
cp validation/reports/*.json release-artifacts/v1.0.0-rc1/
cp rule-engine/tests/conformance/*.json release-artifacts/v1.0.0-rc1/
cp rule-engine/tests/performance/performance_report.json release-artifacts/v1.0.0-rc1/
```
