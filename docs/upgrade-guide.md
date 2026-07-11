# Upgrade Guide — MISRA Compliance Platform

## Upgrading to 1.0.0-rc1 (from 0.x / Phase 8)

### 1. Database Migrations

```bash
# Backup first
pg_dump misra_platform > backup_$(date +%Y%m%d).sql

# Apply migrations
cd backend
alembic upgrade head
```

New tables in `0005_enterprise`:
- `teams`, `team_members`
- `compliance_snapshots`
- `integration_configs`

### 2. Configuration Changes

New environment variables (all optional with safe defaults):

| Variable | Action |
|----------|--------|
| `MISRA_AUTH_REQUIRED` | Set `true` in production |
| `MISRA_PROMETHEUS_ENABLED` | Default `true`; disable if not using Prometheus |
| `MISRA_OTEL_ENABLED` | Enable when OTel collector is deployed |
| `MISRA_API_KEYS` | Add CI service keys |

### 3. Dependency Updates

```bash
cd backend
pip install -e ".[dev]"
pip install -e ".[observability]"  # if using tracing
```

New packages: `prometheus-client`, optional OpenTelemetry stack.

### 4. API Changes (Backward Compatible)

All Phase 8 enterprise endpoints remain unchanged. New in Phase 9:
- `GET /metrics` — Prometheus exposition (root path, not under `/api/v1`)

### 5. Rule Engine

No rule changes in Phase 9. Validation only:
- 152 rules, 96.2% coverage maintained
- Zephyr and mbedTLS corpora added to embedded validation

Re-run validation after upgrade:
```bash
python validation/run_all.py
```

### 6. Frontend

No breaking changes. New routes from Phase 8 remain:
- `/projects/:id/enterprise`
- `/projects/:id/compliance-trends`

### 7. CI Plugins

No changes required. Existing GitHub/GitLab/Jenkins plugins are compatible.

### 8. Kubernetes / Helm

```bash
# Helm upgrade
helm upgrade misra infrastructure/helm/misra-platform \
  --reuse-values \
  --set image.backend.tag=1.0.0-rc1 \
  --set image.frontend.tag=1.0.0-rc1 \
  --set image.clangWorker.tag=1.0.0-rc1
```

### Rollback

```bash
# Database
alembic downgrade 0004_review_workflow

# Helm
helm rollback misra

# Docker
docker compose down
git checkout <previous-tag>
docker compose up --build -d
```

## Upgrading Between RC Versions

1. Run `python validation/run_all.py` on the target version
2. Compare `validation/reports/phase9_validation_summary.json`
3. Review `support_matrix.json` for precision regressions
4. Apply migrations if schema changed
5. Rolling restart backend pods (zero-downtime with 2+ replicas)
