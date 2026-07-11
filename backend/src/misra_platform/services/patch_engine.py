"""Patch generation — export only.

This module never writes to the filesystem and never modifies source files.
It only produces unified-diff / git-patch text that an engineer must apply
manually outside the platform.
"""

import difflib
from dataclasses import dataclass

from misra_platform.services.source_file_service import SourceFileService


@dataclass(slots=True)
class GeneratedPatch:
    unified_diff: str
    git_patch: str
    source_available: bool


class PatchEngine:
    def __init__(self, source_files: SourceFileService | None = None) -> None:
        self.source_files = source_files or SourceFileService()

    def generate(
        self,
        *,
        project_root: str,
        file_path: str,
        line_start: int,
        line_end: int,
        fix_text: str,
        offending_expression: str,
    ) -> GeneratedPatch:
        original_lines = self.source_files.read_line_range(
            project_root, file_path, line_start=line_start, line_end=line_end
        )

        relative_path = self._relative_path(project_root, file_path)
        fix_lines = fix_text.splitlines() or [fix_text]

        if original_lines is not None:
            new_lines = fix_lines
            unified = self._unified_diff(
                relative_path,
                original_lines,
                new_lines,
                start_line=line_start,
            )
            source_available = True
        else:
            # Best-effort synthetic diff when the source file cannot be read
            # (e.g. running outside the mounted project volume). Clearly
            # distinguishable from a real, line-accurate patch.
            unified = self._unified_diff(
                relative_path,
                [offending_expression],
                fix_lines,
                start_line=line_start,
            )
            source_available = False

        git_patch = self._to_git_patch(relative_path, unified)
        return GeneratedPatch(
            unified_diff=unified, git_patch=git_patch, source_available=source_available
        )

    def _relative_path(self, project_root: str, file_path: str) -> str:
        try:
            from pathlib import Path

            return str(Path(file_path).resolve().relative_to(Path(project_root).resolve()))
        except (ValueError, OSError):
            return file_path

    def _unified_diff(
        self,
        relative_path: str,
        original_lines: list[str],
        new_lines: list[str],
        *,
        start_line: int,
    ) -> str:
        original_with_newlines = [f"{line}\n" for line in original_lines]
        new_with_newlines = [f"{line}\n" for line in new_lines]
        diff = difflib.unified_diff(
            original_with_newlines,
            new_with_newlines,
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            lineterm="",
            n=0,
        )
        lines = list(diff)
        return "\n".join(lines)

    def _to_git_patch(self, relative_path: str, unified_diff: str) -> str:
        header = (
            f"diff --git a/{relative_path} b/{relative_path}\n"
            f"index 0000000..0000000 100644\n"
        )
        body_lines = [line for line in unified_diff.splitlines() if not line.startswith(("---", "+++"))]
        return (
            f"{header}--- a/{relative_path}\n+++ b/{relative_path}\n"
            + "\n".join(body_lines)
            + "\n"
        )
