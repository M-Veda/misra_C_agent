"""Phase 8 enterprise integrations — SARIF, CI annotations, PR comments, Jira.

All exporters produce read-only artifacts. No source modification.
Human review workflow and immutable audit trail remain authoritative.
"""

from misra_platform.integrations.enterprise.github_annotations import GitHubAnnotationExporter
from misra_platform.integrations.enterprise.gitlab_annotations import GitLabCodeQualityExporter
from misra_platform.integrations.enterprise.jira_client import JiraIssueClient
from misra_platform.integrations.enterprise.pr_comments import PullRequestCommentBuilder
from misra_platform.integrations.enterprise.sarif_exporter import SarifExporter

__all__ = [
    "GitHubAnnotationExporter",
    "GitLabCodeQualityExporter",
    "JiraIssueClient",
    "PullRequestCommentBuilder",
    "SarifExporter",
]
