# Release Candidate Checklist — v1.0.0-rc1

Use this checklist before promoting `1.0.0-rc1` to `1.0.0` GA.

## Validation

- [ ] `python validation/run_all.py` exits 0 (acceptance gates pass)
- [ ] Embedded corpus: **0 crashes** across 18 functions × 152 rules
- [ ] All 6 codebases covered: STM32 HAL, CMSIS, FreeRTOS, lwIP, Zephyr, mbedTLS
- [ ] Conformance avg precision ≥ 0.95
- [ ] Performance 100K LOC extrapolation ≤ 600 seconds
- [ ] `validation/reports/phase9_validation_summary.json` committed or archived

## False Positive Review

- [ ] Corpus construction artifacts (Rule 8.4) documented separately
- [ ] `support_matrix.json` reviewed for rules below 1.0 precision
- [ ] `unsupported_constructs` list reviewed for release notes

## Backend Tests

- [ ] `cd backend && python -m pytest tests/unit/ -v` — all pass
- [ ] Enterprise integration tests pass (Phase 8)
- [ ] Review workflow tests pass (append-only audit)

## Rule Engine Tests

- [ ] `cd rule-engine && python -m pytest tests/ -v` — all pass
- [ ] 152 rules enabled, 96.2% catalog coverage maintained

## Security

- [ ] `MISRA_AUTH_REQUIRED=true` in production config
- [ ] OIDC issuer/audience/JWKS configured (or API keys for CI only)
- [ ] Secrets not committed (database URL, API keys)
- [ ] CORS origins restricted to production domains

## Observability

- [ ] `GET /metrics` returns Prometheus exposition format
- [ ] ServiceMonitor deployed and scraping in staging
- [ ] OTel tracing verified in staging (if enabled)
- [ ] Health/readiness probes passing under load

## Deployment

- [ ] Docker images built and tagged `1.0.0-rc1`
- [ ] Helm chart installs cleanly in staging cluster
- [ ] Database migration `0005_enterprise` applied
- [ ] `make health` passes against staging deployment
- [ ] SARIF export verified from CI plugin

## Documentation

- [ ] Deployment guide reviewed
- [ ] Upgrade guide covers 0.x → 1.0 migration
- [ ] Operator handbook distributed to on-call team
- [ ] Release notes include unsupported constructs list

## Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineering Lead | | | |
| QA / Validation | | | |
| Security | | | |
| Operations | | | |
