import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class FileIndexNode:
    relative_path: str
    absolute_path: str
    content_hash: str
    include_edges: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IncrementalIndex:
    changed_files: list[str] = field(default_factory=list)
    affected_translation_units: list[str] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_index(project_root: Path, source_files: list[Path]) -> dict[str, FileIndexNode]:
    index: dict[str, FileIndexNode] = {}
    for source_file in source_files:
        if not source_file.exists():
            continue
        relative_path = str(source_file.relative_to(project_root))
        index[relative_path] = FileIndexNode(
            relative_path=relative_path,
            absolute_path=str(source_file.resolve()),
            content_hash=hash_file(source_file),
        )
    return index


def compute_changed_files(
    previous_hashes: dict[str, str],
    current_index: dict[str, FileIndexNode],
) -> list[str]:
    changed: list[str] = []
    for relative_path, current in current_index.items():
        previous_hash = previous_hashes.get(relative_path)
        if previous_hash is None or previous_hash != current.content_hash:
            changed.append(relative_path)
    for relative_path in previous_hashes:
        if relative_path not in current_index:
            changed.append(relative_path)
    return changed


def compute_affected_translation_units(
    changed_files: list[str],
    include_graph: dict[str, list[str]],
    translation_unit_files: list[str],
) -> list[str]:
    affected: set[str] = set()
    reverse_graph: dict[str, set[str]] = {}

    for source, includes in include_graph.items():
        for include in includes:
            reverse_graph.setdefault(include, set()).add(source)

    queue = list(changed_files)
    visited: set[str] = set()

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current in translation_unit_files:
            affected.add(current)

        for dependent in reverse_graph.get(current, set()):
            queue.append(dependent)

    return sorted(affected)
