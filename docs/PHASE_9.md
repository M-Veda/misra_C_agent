# Phase 9 — Industrial Validation & Release Hardening

Phase 9 validates the enterprise compliance platform against industrial embedded codebases, generates release artifacts, and hardens deployment with observability and Kubernetes packaging.

## Validation Targets

| Codebase | Corpus Functions | Status |
|----------|-----------------|--------|
| STM32 HAL | 3 | Validated (synthetic AST) |
| CMSIS | 3 | Validated (synthetic AST) |
| FreeRTOS | 3 | Validated (synthetic AST) |
| lwIP | 3 | Validated (synthetic AST) |
| Zephyr | 3 | **New in Phase 9** |
| mbedTLS | 3 | **New in Phase 9** |

**Total:** 18 functions × 152 rules = 2,736 rule×function pairs per validation run.

## Recorded Metrics

| Category | Source | Output |
|----------|--------|--------|
| **False positives** | Conformance + embedded corpus artifacts | `support_matrix.json` |
| **Unsupported constructs** | `embedded_corpora.py` | `embedded_corpus_report.json` |
| **Crashes** | Embedded corpus crash-safety survey | Must be **0** |
| **Precision** | Conformance harness per rule | `conformance_report.json` |
| **Performance** | 18K LOC synthetic benchmark | `benchmark_report.json` |

## Generated Reports

```
validation/reports/
  phase9_validation_summary.json   # Master rollup + acceptance gate results
  support_matrix.json              # Rule status, precision, FP summary
  compatibility_matrix.json        # Stack/toolchain/CI compatibility
  benchmark_report.json            # Performance projections

rule-engine/tests/conformance/
  conformance_report.json
  embedded_corpus_report.json

rule-engine/tests/performance/
  performance_report.json
```

## Running Validation

```bash
# Full Phase 9 suite
python validation/run_all.py

# Or via Docker
docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.validation.yml run validation

# Individual suites
cd rule-engine
python -m pytest tests/conformance/test_embedded_corpora.py -v
python -m pytest tests/conformance/test_conformance.py -v
python tests/performance/benchmark_rule_engine.py
```

## Acceptance Gates

Defined in `validation/acceptance_gates.json`:

| Gate | Threshold |
|------|-----------|
| Embedded crash count | 0 |
| Conformance avg precision | ≥ 0.95 |
| 100K LOC extrapolation | ≤ 600 seconds |
| Corpora covered | All 6 codebases |

## Observability (Release Hardening)

| Component | Endpoint / Config |
|-----------|----------------|
| **Prometheus** | `GET /metrics` (public, no auth) |
| **OpenTelemetry** | `MISRA_OTEL_ENABLED=true` + collector at `:4317` |
| **Structured logs** | JSON to stdout via structlog |
| **ServiceMonitor** | `infrastructure/k8s/base/servicemonitor.yaml` |

Install OTel dependencies:
```bash
pip install -e "backend[observability]"
```

## Deployment Packaging

| Artifact | Path |
|----------|------|
| Kubernetes manifests | `infrastructure/k8s/base/` |
| Helm chart | `infrastructure/helm/misra-platform/` |
| Prometheus config | `infrastructure/observability/prometheus.yml` |
| OTel collector | `infrastructure/observability/otel-collector.yaml` |

### Helm Install

```bash
helm install misra infrastructure/helm/misra-platform \
  --set database.url="postgresql+asyncpg://..." \
  --set ingress.host=misra.example.com \
  --set auth.required=true
```

### Kustomize Apply

```bash
kubectl apply -k infrastructure/k8s/base/
```

## Release Documentation

| Document | Purpose |
|----------|---------|
| `docs/release-candidate-checklist.md` | Pre-release sign-off |
| `docs/deployment-guide.md` | Production deployment steps |
| `docs/upgrade-guide.md` | Version migration |
| `docs/operator-handbook.md` | Day-2 operations |
| `docs/runbooks/industrial-validation.md` | Validation regeneration |

## Platform Version

**1.0.0-rc1** — Release Candidate 1

## Preserved Guarantees

All Phase 9 work is validation and packaging only:
- Rule engine analyzers unchanged
- Human review workflow unchanged
- Immutable audit trail unchanged
- Patch export only unchanged
