# Deployment Guide — MISRA Compliance Platform v1.0.0-rc1

## Prerequisites

- Docker 24+ and Docker Compose v2
- PostgreSQL 17 (or use bundled compose service)
- Redis 7 (or use bundled compose service)
- 4 GB RAM minimum (8 GB recommended for clang-worker)
- For Kubernetes: cluster 1.28+, Helm 3.14+, ingress controller

## Option 1: Docker Compose (Development / Small Teams)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with production passwords

# Start all services
docker compose up --build -d

# Run database migrations
docker compose exec backend alembic upgrade head

# Verify health
make health
```

Services:
| Service | Port | Purpose |
|---------|------|---------|
| backend | 8000 | API |
| frontend | 5173 | React console |
| nginx | 8080 | Reverse proxy |
| clang-worker | 50051 | AST parsing (gRPC) |
| postgres | 5432 | Persistence |
| redis | 6379 | Cache / rate limiting |

Production overlay:
```bash
docker compose -f docker-compose.yml \
  -f infrastructure/compose/docker-compose.prod.yml up -d
```

## Option 2: Kubernetes (Production)

### Kustomize

```bash
# Edit secrets first
kubectl apply -k infrastructure/k8s/base/

# Verify
kubectl -n misra-platform get pods
kubectl -n misra-platform port-forward svc/misra-backend 8000:8000
curl http://localhost:8000/api/v1/health/ready
```

### Helm

```bash
helm install misra infrastructure/helm/misra-platform \
  --namespace misra-platform --create-namespace \
  --set database.url="postgresql+asyncpg://user:pass@host:5432/misra" \
  --set redis.url="redis://redis:6379/0" \
  --set ingress.host="misra.yourcompany.com" \
  --set auth.required=true \
  --set observability.prometheus.enabled=true
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISRA_DATABASE_URL` | Yes | — | PostgreSQL async URL |
| `MISRA_REDIS_URL` | Yes | — | Redis connection |
| `MISRA_CLANG_WORKER_HOST` | Yes | localhost | gRPC host |
| `MISRA_AUTH_REQUIRED` | Prod | false | Enforce authentication |
| `MISRA_OIDC_ENABLED` | No | false | SSO/OIDC bearer tokens |
| `MISRA_API_KEYS` | CI | [] | Service account keys |
| `MISRA_PROMETHEUS_ENABLED` | No | true | Expose /metrics |
| `MISRA_OTEL_ENABLED` | No | false | Distributed tracing |

## Observability Setup

### Prometheus

Scrape `http://<backend>:8000/metrics`. Sample config:
`infrastructure/observability/prometheus.yml`

Key metrics:
- `misra_http_requests_total`
- `misra_http_request_duration_seconds`
- `misra_analysis_runs_total`
- `misra_rule_engine_duration_seconds`

### OpenTelemetry

```bash
pip install -e "backend[observability]"
```

Set:
```
MISRA_OTEL_ENABLED=true
MISRA_OTEL_EXPORTER_ENDPOINT=http://otel-collector:4317
```

Deploy collector: `infrastructure/observability/otel-collector.yaml`

## Post-Deploy Verification

```bash
# Health
curl https://misra.yourcompany.com/api/v1/health

# Readiness (all dependencies)
curl https://misra.yourcompany.com/api/v1/health/ready

# Metrics
curl https://misra.yourcompany.com/metrics

# Create a project and run analysis (see operator handbook)
```

## CI Integration

After deployment, configure CI plugins:
- GitHub: `integrations/ci/github/action/action.yml`
- GitLab: `integrations/ci/gitlab/misra-compliance.yml`
- Jenkins: `integrations/ci/jenkins/vars/misraCompliance.groovy`

Set `MISRA_API_KEY` in CI secrets and point `api-url` to your deployment.
