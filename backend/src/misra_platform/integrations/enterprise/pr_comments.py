"""Pull request comment builders for GitHub and GitLab."""

from __future__ import annotations

from typing import Any


class PullRequestCommentBuilder:
    def build_review_comment(
        self,
        violations: list[dict[str, Any]],
        *,
        run_id: str,
        platform: str = "github",
    ) -> str:
        if not violations:
            return (
                f"## MISRA Compliance — No violations\n\n"
                f"Run `{run_id}` completed with zero findings.\n\n"
                "_Audit trail preserved. Patch export only._"
            )

        header = f"## MISRA Compliance Review Required\n\nRun `{run_id}` — **{len(violations)}** finding(s).\n\n"
        header += (
            "> **Policy:** Human review required. This bot does not modify source code. "
            "Approved fixes are exported as patches only.\n\n"
        )

        if platform == "gitlab":
            return header + self._gitlab_table(violations)
        return header + self._github_table(violations)

    def build_inline_comments(
        self,
        violations: list[dict[str, Any]],
        *,
        max_comments: int = 50,
    ) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        for violation in violations[:max_comments]:
            comments.append(
                {
                    "path": violation.get("file_path", ""),
                    "line": violation.get("line_start", 1),
                    "body": (
                        f"**{violation.get('rule_id')}** ({violation.get('severity')})\n\n"
                        f"{violation.get('explanation', '')}\n\n"
                        f"_{violation.get('risk_description', '')}_\n\n"
                        "Assign a reviewer before closing."
                    ),
                }
            )
        return comments

    @staticmethod
    def _github_table(violations: list[dict[str, Any]]) -> str:
        rows = []
        for v in violations[:100]:
            rows.append(
                f"| `{v.get('rule_id')}` | `{v.get('file_path')}`:{v.get('line_start')} "
                f"| {v.get('severity')} | {v.get('status', 'open')} |"
            )
        table = "| Rule | Location | Severity | Status |\n|------|----------|----------|--------|\n"
        table += "\n".join(rows)
        if len(violations) > 100:
            table += f"\n\n_…and {len(violations) - 100} more. See SARIF export for full report._"
        return table

    @staticmethod
    def _gitlab_table(violations: list[dict[str, Any]]) -> str:
        lines = []
        for v in violations[:100]:
            lines.append(
                f"- **{v.get('rule_id')}** — `{v.get('file_path')}` line {v.get('line_start')} "
                f"({v.get('severity')})"
            )
        body = "\n".join(lines)
        if len(violations) > 100:
            body += f"\n\n_…and {len(violations) - 100} more._"
        return body
