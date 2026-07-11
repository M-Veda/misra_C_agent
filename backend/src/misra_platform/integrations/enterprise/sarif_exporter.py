"""SARIF 2.1.0 export for enterprise CI/CD and compliance tooling."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any


def _sarif_level(severity: str) -> str:
    mapping = {
        "critical": "error",
        "major": "error",
        "minor": "warning",
        "info": "note",
    }
    return mapping.get(severity.lower(), "warning")


class SarifExporter:
    """Converts platform violations to SARIF 2.1.0 JSON."""

    TOOL_NAME = "misra-compliance-platform"
    TOOL_VERSION = "1.0.0"
    SARIF_VERSION = "2.1.0"

    def export(
        self,
        violations: list[dict[str, Any]],
        *,
        run_id: str,
        project_name: str,
    ) -> dict[str, Any]:
        rules: dict[str, dict[str, Any]] = {}
        results: list[dict[str, Any]] = []

        for violation in violations:
            rule_id = violation["rule_id"]
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": rule_id,
                    "shortDescription": {"text": violation.get("rule_id", rule_id)},
                    "fullDescription": {"text": violation.get("explanation", "")},
                    "defaultConfiguration": {"level": _sarif_level(violation.get("severity", "minor"))},
                    "properties": {
                        "category": violation.get("category"),
                        "confidence": violation.get("confidence_score"),
                    },
                }

            fingerprint = violation.get("fingerprint") or self._fingerprint(violation)
            results.append(
                {
                    "ruleId": rule_id,
                    "ruleIndex": list(rules.keys()).index(rule_id),
                    "level": _sarif_level(violation.get("severity", "minor")),
                    "message": {"text": violation.get("explanation", "")},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": violation.get("file_path", ""),
                                    "uriBaseId": "%SRCROOT%",
                                },
                                "region": {
                                    "startLine": violation.get("line_start", 1),
                                    "endLine": violation.get("line_end", 1),
                                    "startColumn": violation.get("column_start", 1),
                                    "endColumn": violation.get("column_end", 1),
                                },
                            }
                        }
                    ],
                    "partialFingerprints": {"primaryLocationLineHash": fingerprint},
                    "properties": {
                        "status": violation.get("status", "open"),
                        "riskDescription": violation.get("risk_description"),
                        "reviewRequired": True,
                        "patchExportOnly": True,
                    },
                }
            )

        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": self.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.TOOL_NAME,
                            "version": self.TOOL_VERSION,
                            "informationUri": "https://misra-compliance-platform.local",
                            "rules": list(rules.values()),
                        }
                    },
                    "invocations": [
                        {
                            "executionSuccessful": True,
                            "startTimeUtc": datetime.now(UTC).isoformat(),
                            "properties": {"runId": run_id, "projectName": project_name},
                        }
                    ],
                    "results": results,
                }
            ],
        }

    @staticmethod
    def _fingerprint(violation: dict[str, Any]) -> str:
        payload = (
            f"{violation.get('rule_id')}:{violation.get('file_path')}:"
            f"{violation.get('line_start')}:{violation.get('offending_expression')}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
