"""GitLab Code Quality report format."""

from __future__ import annotations

import hashlib
from typing import Any


class GitLabCodeQualityExporter:
    def export(self, violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for violation in violations:
            findings.append(
                {
                    "description": violation.get("explanation", ""),
                    "check_name": violation.get("rule_id", "misra"),
                    "fingerprint": violation.get("fingerprint")
                    or hashlib.md5(
                        f"{violation.get('rule_id')}:{violation.get('file_path')}:{violation.get('line_start')}".encode()
                    ).hexdigest(),
                    "severity": self._gitlab_severity(violation.get("severity", "minor")),
                    "location": {
                        "path": violation.get("file_path", ""),
                        "lines": {"begin": violation.get("line_start", 1)},
                    },
                }
            )
        return findings

    @staticmethod
    def _gitlab_severity(severity: str) -> str:
        mapping = {
            "critical": "blocker",
            "major": "major",
            "minor": "minor",
            "info": "info",
        }
        return mapping.get(severity.lower(), "minor")
