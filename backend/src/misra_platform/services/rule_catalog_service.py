from functools import lru_cache

from misra_platform_rules.coverage_matrix import (
    build_coverage_matrix,
    mark_implemented,
    summary,
)
from misra_platform_rules.registry import RuleRegistry, create_default_registry
from misra_platform_rules.rule_capability_matrix import build_roadmap, roadmap_summary
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata


class RuleCatalogService:
    def __init__(self, registry: RuleRegistry) -> None:
        self.registry = registry

    def list_catalog(self) -> list[RuleMetadata]:
        return sorted(self.registry.list_metadata(), key=lambda item: item.rule_number)

    def get_rule(self, rule_id: str) -> RuleMetadata:
        return self.registry.get_metadata(rule_id)

    def get_examples(self, rule_id: str) -> RuleExamples:
        plugin = self.registry.get(rule_id)
        return plugin.examples()

    def coverage_summary(self) -> dict:
        metadata = self.list_catalog()
        by_standard: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for item in metadata:
            by_standard[item.standard] = by_standard.get(item.standard, 0) + 1
            by_category[item.category] = by_category.get(item.category, 0) + 1
        return {
            "total_rules": len(metadata),
            "by_standard": by_standard,
            "by_category": by_category,
            "implemented_rule_ids": [item.rule_id for item in metadata],
        }

    def full_coverage_matrix(self) -> dict:
        registered_ids = set(self.registry.list_rule_ids())
        entries = mark_implemented(build_coverage_matrix(), registered_ids)
        return {
            "summary": summary(entries),
            "entries": [
                {
                    "identifier": entry.identifier,
                    "kind": entry.kind,
                    "title": entry.title,
                    "category": entry.category.value,
                    "rule_pack": entry.rule_pack.value if entry.rule_pack else None,
                    "misra_class": entry.misra_class,
                    "implemented": entry.implemented_rule_id is not None,
                    "implemented_rule_id": entry.implemented_rule_id,
                    "unsupported_reason": entry.unsupported_reason,
                }
                for entry in entries
            ],
        }

    def implementation_roadmap(self) -> dict:
        registered_ids = set(self.registry.list_rule_ids())
        roadmap = build_roadmap(registered_ids)
        return {
            "summary": roadmap_summary(roadmap),
            "entries": [entry.as_dict() for entry in roadmap],
        }


@lru_cache
def get_rule_catalog_service() -> RuleCatalogService:
    return RuleCatalogService(create_default_registry())
