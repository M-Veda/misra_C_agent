import importlib
from pathlib import Path
from typing import Any

import yaml

from misra_platform_rules.base_rule import IRulePlugin
from misra_platform_rules.rule_result import RuleMetadata


class RuleRegistryError(Exception):
    pass


class RuleRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, IRulePlugin] = {}
        self._metadata: dict[str, RuleMetadata] = {}
        self._manifest_versions: dict[str, str] = {}

    def load_standard(self, manifest_path: Path) -> None:
        if not manifest_path.exists():
            raise RuleRegistryError(f"Manifest not found: {manifest_path}")

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise RuleRegistryError(f"Invalid manifest format: {manifest_path}")

        standard = manifest.get("standard")
        version = manifest.get("version", "0.0.0")
        extends = manifest.get("extends")
        rules = manifest.get("rules", [])

        if not standard:
            raise RuleRegistryError(f"Manifest missing standard: {manifest_path}")

        if extends and extends not in self._manifest_versions:
            raise RuleRegistryError(f"Dependency standard not loaded: {extends}")

        if standard in self._manifest_versions:
            self._validate_version_compatibility(standard, version, self._manifest_versions[standard])

        seen_rule_ids: set[str] = set()
        for entry in rules:
            self._register_manifest_entry(entry, seen_rule_ids)

        self._manifest_versions[standard] = version

    def _validate_version_compatibility(self, standard: str, new_version: str, existing: str) -> None:
        if new_version != existing:
            raise RuleRegistryError(
                f"Version mismatch for {standard}: existing {existing}, attempted {new_version}"
            )

    def _register_manifest_entry(self, entry: dict[str, Any], seen_rule_ids: set[str]) -> None:
        rule_id = entry.get("rule_id")
        module_path = entry.get("module")
        class_name = entry.get("class_name")
        dependencies: list[str] = entry.get("dependencies", [])

        if not rule_id or not module_path or not class_name:
            raise RuleRegistryError("Manifest entry missing rule_id, module, or class_name")

        if rule_id in seen_rule_ids:
            raise RuleRegistryError(f"Duplicate rule in manifest: {rule_id}")
        seen_rule_ids.add(rule_id)

        if rule_id in self._plugins:
            raise RuleRegistryError(f"Duplicate rule registration: {rule_id}")

        for dependency in dependencies:
            if dependency not in self._plugins:
                raise RuleRegistryError(f"Unresolved rule dependency {dependency} for {rule_id}")

        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        plugin: IRulePlugin = plugin_class()

        metadata = plugin.metadata
        if metadata.rule_id != rule_id:
            raise RuleRegistryError(
                f"Metadata rule_id {metadata.rule_id} does not match manifest {rule_id}"
            )

        self._plugins[rule_id] = plugin
        self._metadata[rule_id] = metadata

    def discover(self, standards_root: Path) -> None:
        if not standards_root.exists():
            raise RuleRegistryError(f"Standards root not found: {standards_root}")

        manifests = sorted(standards_root.glob("*/manifest.yaml"))
        if not manifests:
            raise RuleRegistryError(f"No manifests found under {standards_root}")

        for manifest_path in manifests:
            self.load_standard(manifest_path)

    def get(self, rule_id: str) -> IRulePlugin:
        if rule_id not in self._plugins:
            raise RuleRegistryError(f"Rule not registered: {rule_id}")
        return self._plugins[rule_id]

    def list_metadata(self) -> list[RuleMetadata]:
        return list(self._metadata.values())

    def get_metadata(self, rule_id: str) -> RuleMetadata:
        if rule_id not in self._metadata:
            raise RuleRegistryError(f"Rule metadata not found: {rule_id}")
        return self._metadata[rule_id]

    def list_rule_ids(self) -> list[str]:
        return sorted(self._plugins.keys())

    def select_rules(self, enabled_rules: list[str] | None = None) -> list[IRulePlugin]:
        if not enabled_rules:
            return list(self._plugins.values())
        return [self._plugins[rule_id] for rule_id in enabled_rules if rule_id in self._plugins]


def create_default_registry() -> RuleRegistry:
    standards_root = Path(__file__).resolve().parent / "standards"
    registry = RuleRegistry()
    registry.discover(standards_root)
    return registry
