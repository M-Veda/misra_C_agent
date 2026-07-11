import json
from pathlib import Path

from misra_platform.core.config import Settings


class LocalArtifactStorage:
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.artifact_storage_path)

    def ast_cache_path(self, project_id: str, run_id: str, translation_unit_id: str) -> Path:
        path = self.root / "ast_cache" / project_id / run_id / f"{translation_unit_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_ast_artifact(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def read_ast_artifact(self, path: Path | str) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))
