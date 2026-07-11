"""GitHub Actions workflow command annotations."""

from __future__ import annotations

from typing import Any


class GitHubAnnotationExporter:
    def export(self, violations: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for violation in violations:
            level = "error" if violation.get("severity") in ("critical", "major") else "warning"
            file_path = violation.get("file_path", "")
            line = violation.get("line_start", 1)
            col = violation.get("column_start", 1)
            message = (
                f"[{violation.get('rule_id')}] {violation.get('explanation', '')} "
                f"(confidence: {round(float(violation.get('confidence_score', 0)) * 100)}%)"
            )
            lines.append(f"::{level} file={file_path},line={line},col={col}::{message}")
        return lines

    def export_summary_markdown(self, violations: list[dict[str, Any]], *, run_id: str) -> str:
        by_rule: dict[str, int] = {}
        for v in violations:
            by_rule[v.get("rule_id", "unknown")] = by_rule.get(v.get("rule_id", "unknown"), 0) + 1

        rows = "\n".join(f"| {rule} | {count} |" for rule, count in sorted(by_rule.items()))
        return (
            f"## MISRA Compliance Scan (`{run_id}`)\n\n"
            f"**Total findings:** {len(violations)}\n\n"
            f"| Rule | Count |\n|------|-------|\n{rows}\n\n"
            "_Human review required. Patches are export-only — no auto-fix applied._"
        )
