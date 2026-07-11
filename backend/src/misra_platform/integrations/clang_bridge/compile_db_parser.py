import json
import re
import shlex
from pathlib import Path

from misra_platform.integrations.clang_bridge.compile_commands import (
    CompileCommandEntry,
    CompileCommandsValidation,
)

_RESPONSE_FILE_PATTERN = re.compile(r"^@(.+)$")


def _expand_response_file(argument: str, base_directory: Path) -> list[str]:
    match = _RESPONSE_FILE_PATTERN.match(argument)
    if not match:
        return [argument]

    response_path = Path(match.group(1))
    if not response_path.is_absolute():
        response_path = base_directory / response_path

    if not response_path.exists():
        return [argument]

    content = response_path.read_text(encoding="utf-8", errors="replace")
    return shlex.split(content, posix=False)


def _normalize_arguments(raw_arguments: list[str], directory: Path) -> list[str]:
    expanded: list[str] = []
    for argument in raw_arguments:
        expanded.extend(_expand_response_file(argument, directory))
    return expanded


def _parse_entry(raw_entry: dict) -> CompileCommandEntry | None:
    directory = raw_entry.get("directory")
    file_name = raw_entry.get("file")
    if not directory or not file_name:
        return None

    directory_path = Path(directory)
    if "arguments" in raw_entry and isinstance(raw_entry["arguments"], list):
        arguments = [str(value) for value in raw_entry["arguments"]]
    elif "command" in raw_entry and isinstance(raw_entry["command"], str):
        arguments = shlex.split(raw_entry["command"], posix=False)
    else:
        return None

    normalized_arguments = _normalize_arguments(arguments, directory_path)
    return CompileCommandEntry(
        file=str(file_name),
        directory=str(directory_path),
        arguments=normalized_arguments,
        output=str(raw_entry["output"]) if raw_entry.get("output") else None,
    )


def load_compile_commands(path: Path) -> CompileCommandsValidation:
    diagnostics: list[str] = []
    if not path.exists():
        return CompileCommandsValidation(
            is_valid=False,
            source=str(path),
            diagnostics=[f"compile_commands.json not found: {path}"],
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return CompileCommandsValidation(
            is_valid=False,
            source=str(path),
            diagnostics=[f"Invalid JSON: {error}"],
        )

    if not isinstance(payload, list):
        return CompileCommandsValidation(
            is_valid=False,
            source=str(path),
            diagnostics=["compile_commands.json must contain a JSON array"],
        )

    entries: list[CompileCommandEntry] = []
    seen_fingerprints: set[str] = set()
    duplicate_count = 0

    for index, raw_entry in enumerate(payload):
        if not isinstance(raw_entry, dict):
            diagnostics.append(f"Entry {index} is not an object")
            continue

        parsed = _parse_entry(raw_entry)
        if parsed is None:
            diagnostics.append(f"Entry {index} is missing required fields")
            continue

        absolute_file = Path(parsed.absolute_file)
        if not absolute_file.exists():
            diagnostics.append(f"Source file not found: {absolute_file}")

        if parsed.fingerprint in seen_fingerprints:
            duplicate_count += 1
            continue

        seen_fingerprints.add(parsed.fingerprint)
        entries.append(parsed)

    is_valid = len(entries) > 0
    if not entries:
        diagnostics.append("No valid translation units found")

    return CompileCommandsValidation(
        is_valid=is_valid,
        source=str(path),
        entries=entries,
        diagnostics=diagnostics,
        duplicate_count=duplicate_count,
    )


def deduplicate_entries(entries: list[CompileCommandEntry]) -> list[CompileCommandEntry]:
    seen: set[str] = set()
    unique_entries: list[CompileCommandEntry] = []
    for entry in entries:
        if entry.fingerprint in seen:
            continue
        seen.add(entry.fingerprint)
        unique_entries.append(entry)
    return unique_entries
