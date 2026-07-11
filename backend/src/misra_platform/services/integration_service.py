"""Enterprise integration dispatch — PR comments, Jira sync, audit logging."""

from __future__ import annotations

import uuid

from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.integrations.enterprise.jira_client import JiraIssueClient
from misra_platform.integrations.enterprise.pr_comments import PullRequestCommentBuilder
from misra_platform.repositories.enterprise_repo import EnterpriseRepository
from misra_platform.services.export_service import violation_to_dict


class IntegrationService:
    def __init__(self, enterprise_repo: EnterpriseRepository) -> None:
        self.enterprise_repo = enterprise_repo
        self.pr_builder = PullRequestCommentBuilder()

    def build_pr_comment(
        self,
        violations: list[ViolationRecord],
        *,
        run_id: uuid.UUID,
        platform: str = "github",
    ) -> str:
        payload = [violation_to_dict(v) for v in violations]
        return self.pr_builder.build_review_comment(payload, run_id=str(run_id), platform=platform)

    def build_inline_pr_comments(
        self,
        violations: list[ViolationRecord],
        *,
        max_comments: int = 50,
    ) -> list[dict]:
        return self.pr_builder.build_inline_comments(
            [violation_to_dict(v) for v in violations], max_comments=max_comments
        )

    async def log_export_event(
        self,
        *,
        run_id: uuid.UUID,
        format_name: str,
        actor_id: str,
        actor_name: str | None,
        violation_count: int,
    ) -> None:
        await self.enterprise_repo.append_audit(
            entity_type="analysis_run",
            entity_id=str(run_id),
            action=f"export_{format_name}",
            actor_id=actor_id,
            actor_name=actor_name,
            new_state={"format": format_name, "violation_count": violation_count},
            notes="Export-only artifact. No source modification.",
        )

    async def sync_to_jira(
        self,
        *,
        violations: list[ViolationRecord],
        run_id: uuid.UUID,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        actor_id: str,
        actor_name: str | None,
        max_issues: int = 25,
    ) -> list[dict]:
        client = JiraIssueClient(
            base_url=base_url,
            email=email,
            api_token=api_token,
            project_key=project_key,
        )
        try:
            created = await client.sync_violations(
                [violation_to_dict(v) for v in violations],
                run_id=str(run_id),
                max_issues=max_issues,
            )
        finally:
            await client.close()

        await self.enterprise_repo.append_audit(
            entity_type="analysis_run",
            entity_id=str(run_id),
            action="jira_sync",
            actor_id=actor_id,
            actor_name=actor_name,
            new_state={"issues_created": len(created), "max_issues": max_issues},
            notes="Jira issues created for human review. No auto-fix applied.",
        )
        return created
