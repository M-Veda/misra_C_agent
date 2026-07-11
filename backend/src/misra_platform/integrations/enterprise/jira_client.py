"""Jira REST API client for violation-to-issue sync."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class JiraIssuePayload:
    summary: str
    description: str
    issue_type: str = "Task"
    labels: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class JiraIssueClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_key = project_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(email, api_token),
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_issue(self, payload: JiraIssuePayload) -> dict[str, Any]:
        body: dict[str, Any] = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": payload.summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": payload.description}],
                        }
                    ],
                },
                "issuetype": {"name": payload.issue_type},
                "labels": payload.labels or ["misra-compliance"],
            }
        }
        if payload.custom_fields:
            body["fields"].update(payload.custom_fields)

        response = await self._client.post("/rest/api/3/issue", json=body)
        response.raise_for_status()
        return response.json()

    def violation_to_payload(self, violation: dict[str, Any], *, run_id: str) -> JiraIssuePayload:
        summary = (
            f"MISRA {violation.get('rule_id')} — "
            f"{violation.get('file_path')}:{violation.get('line_start')}"
        )
        description = (
            f"Rule: {violation.get('rule_id')}\n"
            f"File: {violation.get('file_path')}\n"
            f"Line: {violation.get('line_start')}\n"
            f"Severity: {violation.get('severity')}\n"
            f"Category: {violation.get('category')}\n"
            f"Confidence: {violation.get('confidence_score')}\n\n"
            f"{violation.get('explanation', '')}\n\n"
            f"Risk: {violation.get('risk_description', '')}\n\n"
            f"Analysis run: {run_id}\n"
            f"Fingerprint: {violation.get('fingerprint', '')}\n\n"
            "Human review required. No auto-fix applied."
        )
        return JiraIssuePayload(
            summary=summary[:255],
            description=description,
            labels=["misra-compliance", violation.get("rule_id", "misra")],
        )

    async def sync_violations(
        self,
        violations: list[dict[str, Any]],
        *,
        run_id: str,
        max_issues: int = 25,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for violation in violations[:max_issues]:
            payload = self.violation_to_payload(violation, run_id=run_id)
            result = await self.create_issue(payload)
            created.append({"violation_fingerprint": violation.get("fingerprint"), "jira": result})
        return created
