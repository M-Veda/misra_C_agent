from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class CompileCommandEntry:
    file: str
    directory: str
    arguments: list[str]
    output: str | None = None

    @property
    def absolute_file(self) -> str:
        file_path = Path(self.file)
        if file_path.is_absolute():
            return str(file_path.resolve())
        return str((Path(self.directory) / file_path).resolve())

    @property
    def fingerprint(self) -> str:
        import hashlib

        payload = "|".join([self.directory, self.absolute_file, *self.arguments])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class CompileCommandsValidation:
    is_valid: bool
    source: str
    entries: list[CompileCommandEntry] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    duplicate_count: int = 0
