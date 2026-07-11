"""Unit tests for Phase 8 enterprise exporters and integrations."""

import uuid

import pytest
from httpx import AsyncClient

from misra_platform.domain.models.analysis import AnalysisRun, Project
from misra_platform.domain.models.enterprise import TeamMemberRecord, TeamRecord
from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.integrations.enterprise.github_annotations import GitHubAnnotationExporter
from misra_platform.integrations.enterprise.gitlab_annotations import GitLabCodeQualityExporter
from misra_platform.integrations.enterprise.sarif_exporter import SarifExporter
from misra_platform.repositories.base import session_scope
from misra_platform.services.compliance_analytics_service import ComplianceAnalyticsService
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.repositories.violation_repo import ViolationRepository


def _sample_violation() -> dict:
    return {
        "rule_id": "misra-c2012-rule-10-3",
        "fingerprint": "fp-test-001",
        "file_path": "src/rpm.c",
        "line_start": 10,
        "line_end": 10,
        "column_start": 1,
        "column_end": 20,
        "severity": "major",
        "confidence_score": 0.9,
        "category": "required",
        "explanation": "Narrowing assignment detected.",
        "risk_description": "Value truncation may occur.",
        "status": "open",
    }


def test_sarif_exporter_produces_valid_structure() -> None:
    exporter = SarifExporter()
    result = exporter.export(
        [_sample_violation()],
        run_id="run-1",
        project_name="Test Project",
    )
    assert result["version"] == "2.1.0"
    assert len(result["runs"]) == 1
    assert result["runs"][0]["results"][0]["ruleId"] == "misra-c2012-rule-10-3"
    assert result["runs"][0]["results"][0]["properties"]["patchExportOnly"] is True


def test_github_annotation_exporter() -> None:
    exporter = GitHubAnnotationExporter()
    lines = exporter.export([_sample_violation()])
    assert len(lines) == 1
    assert lines[0].startswith("::error file=src/rpm.c,line=10,col=1::")


def test_gitlab_codequality_exporter() -> None:
    exporter = GitLabCodeQualityExporter()
    findings = exporter.export([_sample_violation()])
    assert findings[0]["check_name"] == "misra-c2012-rule-10-3"
    assert findings[0]["severity"] == "major"
    assert findings[0]["location"]["path"] == "src/rpm.c"


async def _seed_run_with_violation() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    async with session_scope() as session:
        project = Project(
            name="Enterprise Project",
            root_path="/workspace/samples",
            toolchain_profile_id="clang-host",
        )
        session.add(project)
        await session.flush()

        run = AnalysisRun(project_id=project.id, run_type="full", status="completed")
        session.add(run)
        await session.flush()

        violation = ViolationRecord(
            analysis_run_id=run.id,
            project_id=project.id,
            rule_id="misra-c2012-rule-10-3",
            fingerprint="fp-enterprise-" + str(uuid.uuid4()),
            file_path="src/rpm.c",
            line_start=10,
            line_end=10,
            column_start=1,
            column_end=20,
            severity="major",
            confidence_score=0.9,
            category="required",
            offending_expression="uint8_t narrow = wide;",
            explanation="Narrowing assignment detected.",
            risk_description="Value truncation may occur.",
            source_snippet="src/rpm.c:10",
            ast_node_reference="node-1",
            status="open",
        )
        session.add(violation)
        await session.flush()
        return project.id, run.id, violation.id


@pytest.mark.asyncio
async def test_sarif_export_endpoint(client: AsyncClient) -> None:
    _, run_id, _ = await _seed_run_with_violation()
    response = await client.get(f"/api/v1/analysis/runs/{run_id}/export/sarif")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/sarif+json")


@pytest.mark.asyncio
async def test_github_annotations_endpoint(client: AsyncClient) -> None:
    _, run_id, _ = await _seed_run_with_violation()
    response = await client.get(f"/api/v1/analysis/runs/{run_id}/export/github-annotations")
    assert response.status_code == 200
    payload = response.json()
    assert "annotations" in payload
    assert len(payload["annotations"]) == 1


@pytest.mark.asyncio
async def test_pr_comment_endpoint(client: AsyncClient) -> None:
    _, run_id, _ = await _seed_run_with_violation()
    response = await client.post(
        f"/api/v1/analysis/runs/{run_id}/integrations/pr-comment",
        json={"platform": "github"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "MISRA Compliance Review Required" in payload["body"]


@pytest.mark.asyncio
async def test_reviewer_assignment(client: AsyncClient) -> None:
    project_id, run_id, violation_id = await _seed_run_with_violation()

    async with session_scope() as session:
        team = TeamRecord(name="Firmware Team", description="Reviewers")
        session.add(team)
        await session.flush()
        session.add(
            TeamMemberRecord(
                team_id=team.id,
                user_id="eng-42",
                display_name="Alex Reviewer",
                role="reviewer",
            )
        )
        team_id = team.id

    response = await client.post(
        f"/api/v1/violations/{violation_id}/assign-reviewer",
        json={
            "reviewer_id": "eng-42",
            "reviewer_name": "Alex Reviewer",
            "actor_id": "lead-1",
            "team_id": str(team_id),
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["assigned_reviewer_id"] == "eng-42"


@pytest.mark.asyncio
async def test_compliance_snapshot_and_trends(client: AsyncClient) -> None:
    project_id, run_id, _ = await _seed_run_with_violation()

    snapshot_response = await client.post(
        f"/api/v1/analysis/runs/{run_id}/compliance-snapshot",
        json={},
    )
    assert snapshot_response.status_code == 201

    dashboard_response = await client.get(f"/api/v1/projects/{project_id}/dashboard")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["violations_open"] == 1

    trends_response = await client.get(f"/api/v1/projects/{project_id}/compliance-trends")
    assert trends_response.status_code == 200
    trends = trends_response.json()
    assert len(trends) == 1


@pytest.mark.asyncio
async def test_compliance_score_computation() -> None:
    async with session_scope() as session:
        enterprise_repo = EnterpriseRepository(session)
        violation_repo = ViolationRepository(session)
        service = ComplianceAnalyticsService(enterprise_repo, violation_repo)
        score = service.compute_compliance_score(
            violations_total=10,
            violations_resolved=5,
            rules_executed=152,
        )
        assert 0 <= score <= 100
