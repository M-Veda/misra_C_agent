import json
from pathlib import Path

from misra_platform.core.config import Settings


class ToolchainProfileService:
    def __init__(self, settings: Settings) -> None:
        self.profile_dir = Path(settings.toolchain_profile_dir)

    def list_profiles(self) -> list[dict]:
        profiles: list[dict] = []
        if not self.profile_dir.exists():
            return profiles
        for profile_path in sorted(self.profile_dir.glob("*.json")):
            profiles.append(json.loads(profile_path.read_text(encoding="utf-8")))
        return profiles

    def get_profile(self, profile_id: str) -> dict | None:
        profile_path = self.profile_dir / f"{profile_id}.json"
        if not profile_path.exists():
            return None
        return json.loads(profile_path.read_text(encoding="utf-8"))
