"""Sandboxed, read-only access to project source files.

Used by the review workspace to display source code and by the patch engine
to compute real unified diffs. Never writes to disk.
"""

from dataclasses import dataclass
from pathlib import Path


class SourceAccessError(Exception):
    pass


@dataclass(slots=True)
class SourceWindow:
    file_path: str
    start_line: int
    end_line: int
    lines: list[str]
    highlight_start: int
    highlight_end: int
    available: bool


class SourceFileService:
    """Reads source files strictly within a project's root path."""

    def _resolve(self, project_root: str, file_path: str) -> Path | None:
        try:
            root = Path(project_root).resolve()
            target = Path(file_path).resolve()
        except OSError:
            return None
        if root != target and root not in target.parents:
            return None
        if not target.exists() or not target.is_file():
            return None
        return target

    def read_lines(self, project_root: str, file_path: str) -> list[str] | None:
        resolved = self._resolve(project_root, file_path)
        if resolved is None:
            return None
        try:
            return resolved.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None

    def read_window(
        self,
        project_root: str,
        file_path: str,
        *,
        line_start: int,
        line_end: int,
        context: int = 25,
    ) -> SourceWindow:
        lines = self.read_lines(project_root, file_path)
        if lines is None:
            return SourceWindow(
                file_path=file_path,
                start_line=max(line_start - context, 1),
                end_line=line_end + context,
                lines=[],
                highlight_start=line_start,
                highlight_end=line_end,
                available=False,
            )

        window_start = max(line_start - context, 1)
        window_end = min(line_end + context, len(lines))
        window_lines = lines[window_start - 1 : window_end]

        return SourceWindow(
            file_path=file_path,
            start_line=window_start,
            end_line=window_end,
            lines=window_lines,
            highlight_start=line_start,
            highlight_end=line_end,
            available=True,
        )

    def read_line_range(
        self, project_root: str, file_path: str, *, line_start: int, line_end: int
    ) -> list[str] | None:
        lines = self.read_lines(project_root, file_path)
        if lines is None:
            return None
        if line_start < 1 or line_end > len(lines) or line_start > line_end:
            return None
        return lines[line_start - 1 : line_end]
