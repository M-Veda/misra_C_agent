# Operator Handbook — MISRA Compliance Platform

Day-2 operations guide for platform administrators.

## Daily Health Checks

```bash
# Quick status
curl -s https://<host>/api/v1/health | jq .
curl -s https://<host>/api/v1/health/ready | jq .

# All dependencies must show "up"
# Returns 503 if any dependency is degraded
```

Expected readiness checks: `database`, `redis`, `clang_worker`.

## Monitoring

### Prometheus Alerts (Recommended)

| Alert | Condition | Severity |
|-------|-----------|----------|
| `MisraBackendDown` | `up{job="misra-backend"} == 0` for 2m | critical |
| `MisraHighErrorRate` | 5xx rate > 5% over 5m | warning |
| `MisraSlowAnalysis` | `misra_rule_engine_duration_seconds` p99 > 120s | warning |
| `MisraClangWorkerDown` | readiness check `clang_worker` down | critical |

### Key Dashboards

1. **Platform Health** — request rate, error rate, latency p50/p99
2. **Analysis Pipeline** — `misra_analysis_runs_total` by status
3. **Compliance Trends** — `/api/v1/projects/{id}/compliance-trends`
4. **Review Workflow** — `/api/v1/metrics/review-acceptance-rate`

### Logs

Structured JSON to stdout. Search by `X-Correlation-ID` header for request tracing.

```bash
kubectl -n misra-platform logs -l app=misra-backend -f | jq .
```

## Common Operations

### Restart Services

```bash
# Docker Compose
docker compose restart backend clang-worker

# Kubernetes
kubectl -n misra-platform rollout restart deployment/misra-backend
kubectl -n misra-platform rollout restart deployment/misra-clang-worker
```

### Database Maintenance

```bash
# Check connection count
docker compose exec postgres psql -U misra -c "SELECT count(*) FROM pg_stat_activity;"

# Vacuum (low-traffic window)
docker compose exec postgres vacuumdb -U misra -d misra_platform --analyze
```

Audit tables (`audit_entries`, `violation_reviews`) are append-only — never truncate in production.

### Run Analysis

1. Register project: `POST /api/v1/projects`
2. Upload `compile_commands.json`
3. Trigger analysis: `POST /api/v1/projects/{id}/analysis`
4. Monitor progress via frontend or API
5. Export SARIF: `GET /api/v1/analysis/runs/{run_id}/export/sarif`

### Reviewer Assignment

```bash
# Round-robin for a team
curl -X POST https://<host>/api/v1/integrations/round-robin-assign \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"run_id":"<uuid>","team_id":"<uuid>","actor_id":"ops"}'
```

## Incident Response

### Backend Unhealthy

1. Check `/api/v1/health/ready` — identify degraded dependency
2. If database: check postgres pod/container, connection pool exhaustion
3. If redis: check memory usage, restart redis
4. If clang-worker: check gRPC connectivity, restart worker (stateless)

### Analysis Stuck

1. Check backend logs for `analysis_run_id`
2. Verify clang-worker health: `infrastructure/scripts/healthcheck-clang.sh`
3. Check `analysis_runs` table for status
4. Cancel and retry if timeout exceeded (`MISRA_CLANG_WORKER_PARSE_TIMEOUT_SECONDS`)

### High Memory on clang-worker

- Reduce concurrent translation units
- Increase pod memory limits
- Scale clang-worker replicas (stateless, load-balance via k8s service)

## Backup & Recovery

### What to Back Up

| Asset | Method | Frequency |
|-------|--------|-----------|
| PostgreSQL | `pg_dump` | Daily |
| Artifacts volume | Volume snapshot | Daily |
| Configuration | Git / Helm values | On change |
| Validation reports | Archive to object storage | Per release |

### Recovery

```bash
psql -U misra misra_platform < backup.sql
docker compose restart backend
```

## Security Operations

- Rotate `MISRA_API_KEYS` quarterly
- Review `audit_entries` for anomalous export/jira-sync activity
- OIDC token validation logs appear when `MISRA_AUTH_REQUIRED=true`
- Never enable auto-fix — patches are export-only by design

## Validation Re-run (Release)

Before any platform upgrade:
```bash
python validation/run_all.py
```

See `docs/runbooks/industrial-validation.md` for detailed steps.

## Support Contacts

| Area | Escalation |
|------|-----------|
| Platform outage | On-call SRE |
| False positive report | Compliance engineering |
| Rule engine crash | Rule engine team |
| CI integration | DevOps / platform team |
