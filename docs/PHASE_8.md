# Phase 8 — Enterprise Compliance Product

Phase 8 transforms the MISRA platform from an analyzer into an enterprise compliance product. All new capabilities sit **on top of** the existing rule engine, human review workflow, and immutable audit trail. No analyzer code was modified.

## Delivered Features

| Feature | Implementation |
|---------|----------------|
| **SARIF export** | `SarifExporter` + `GET /api/v1/analysis/runs/{run_id}/export/sarif` |
| **GitHub annotations** | `GitHubAnnotationExporter` + workflow command endpoint |
| **GitLab annotations** | `GitLabCodeQualityExporter` + codequality JSON endpoint |
| **Jenkins integration** | `integrations/ci/jenkins/` shared library + Jenkinsfile |
| **PR comments** | `PullRequestCommentBuilder` + `POST .../integrations/pr-comment` |
| **Reviewer assignment** | `ReviewerAssignmentService` + assign/bulk/round-robin APIs |
| **Multi-user workflow** | `TeamRecord`, `TeamMemberRecord`, teams API |
| **SSO/OIDC** | `OidcAuthenticator` + `AuthMiddleware` (Bearer + X-API-Key) |
| **Team dashboards** | `ComplianceAnalyticsService` + `TeamDashboardPage` |
| **Compliance trends** | `ComplianceSnapshotRecord` + trends API + `ComplianceTrendsPage` |
| **Historical analytics** | Immutable snapshots per analysis run |
| **Jira integration** | `JiraIssueClient` + `POST .../integrations/jira-sync` |
| **CI/CD plugins** | GitHub Action, GitLab CI component, Jenkins shared library |

## Preserved Guarantees

1. **Immutable audit trail** — Every export, Jira sync, and reviewer assignment appends to `audit_entries`.
2. **Human review workflow** — Review service unchanged; violations require explicit engineer action.
3. **Patch export only** — SARIF/CI artifacts are read-only; `PatchEngine` never auto-applies fixes.
4. **Analyzer reuse** — Rule engine and clang-worker untouched; enterprise layer consumes persisted violations.

## Architecture

```
CI/CD (GitHub / GitLab / Jenkins)
        │
        ▼
┌───────────────────────────────────────┐
│  Enterprise API Layer (Phase 8)       │
│  exports · integrations · teams ·     │
│  compliance analytics · OIDC auth     │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Review Workflow (Phase 2)            │
│  append-only reviews · patches · audit│
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  Rule Engine (Phases 6–7.1)           │
│  152 rules · 96.2% coverage           │
└───────────────────────────────────────┘
```

## API Endpoints

### Exports
- `GET /api/v1/analysis/runs/{run_id}/export/sarif`
- `GET /api/v1/analysis/runs/{run_id}/export/github-annotations`
- `GET /api/v1/analysis/runs/{run_id}/export/gitlab-codequality`

### Integrations
- `POST /api/v1/analysis/runs/{run_id}/integrations/pr-comment`
- `POST /api/v1/analysis/runs/{run_id}/integrations/jira-sync`
- `POST /api/v1/violations/{violation_id}/assign-reviewer`
- `POST /api/v1/violations/bulk-assign-reviewer`
- `POST /api/v1/integrations/round-robin-assign`

### Teams & Analytics
- `POST /api/v1/teams` · `GET /api/v1/teams` · `GET /api/v1/teams/{team_id}`
- `POST /api/v1/teams/{team_id}/members`
- `GET /api/v1/projects/{project_id}/dashboard`
- `GET /api/v1/projects/{project_id}/compliance-trends`
- `POST /api/v1/analysis/runs/{run_id}/compliance-snapshot`

## Configuration

Environment variables (prefix `MISRA_`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_REQUIRED` | `false` | Enforce authentication on all non-public routes |
| `OIDC_ENABLED` | `false` | Enable OIDC bearer token validation |
| `OIDC_ISSUER` | — | OIDC issuer URL |
| `OIDC_AUDIENCE` | — | Expected JWT audience |
| `OIDC_JWKS_URI` | — | JWKS endpoint for token verification |
| `API_KEYS` | `[]` | CI service API keys (comma-separated) |

## CI/CD Plugins

### GitHub Actions
```yaml
- uses: ./integrations/ci/github/action
  with:
    api-url: https://misra.example.com
    api-key: ${{ secrets.MISRA_API_KEY }}
    run-id: ${{ steps.analysis.outputs.run_id }}
    team-id: ${{ vars.MISRA_TEAM_ID }}
```

### GitLab CI
```yaml
include:
  - local: integrations/ci/gitlab/misra-compliance.yml
```

### Jenkins
```groovy
@Library('misra-compliance') _
misraCompliance(
  apiUrl: 'http://misra-platform:8000',
  runId: env.MISRA_RUN_ID,
  apiKey: credentials('misra-api-key'),
  teamId: env.MISRA_TEAM_ID
)
```

## Database Migration

`0005_enterprise` adds:
- `teams` / `team_members`
- `compliance_snapshots` (immutable historical metrics)
- `integration_configs` (per-project provider settings)

## Frontend

- `/projects/:projectId/enterprise` — Team compliance dashboard
- `/projects/:projectId/compliance-trends` — Historical analytics table

## Tests

```bash
cd backend && pytest tests/unit/test_enterprise_integrations.py -v
```

Covers SARIF structure, GitHub/GitLab exporters, API endpoints, reviewer assignment, and compliance snapshots.

## Rule Engine Status (unchanged)

| Metric | Value |
|--------|-------|
| Implemented rules | 152 / 158 |
| Coverage | 96.2% |
| Analyzer reuse | 100% |
