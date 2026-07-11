from dataclasses import dataclass, field

from misra_platform_rules.execution_planner import (
    CyclicRuleDependencyError,
    resolve_execution_groups,
)
from misra_platform_rules.registry import create_default_registry
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


@dataclass(slots=True)
class _FakeRule:
    rule_id: str
    implementation_category: str = "A_ast_only"
    rule_dependencies: list[str] = field(default_factory=list)

    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id=self.rule_id,
            rule_number=self.rule_id,
            standard="misra_c_2012",
            category="required",
            severity="medium",
            title=self.rule_id,
            description="",
            rationale="",
            plugin_module="fake",
            implementation_category=self.implementation_category,
            rule_dependencies=self.rule_dependencies,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        return []

    def explain(self, result: RuleResult) -> str:
        return ""

    def generate_fix(self, result: RuleResult) -> SuggestedFix | None:
        return None

    def examples(self) -> RuleExamples:
        return RuleExamples()


def test_resolve_execution_groups_orders_by_category_tier():
    rules = [
        _FakeRule("g-rule", implementation_category="G_configuration_build"),
        _FakeRule("a-rule", implementation_category="A_ast_only"),
        _FakeRule("c-rule", implementation_category="C_control_flow"),
    ]
    groups = resolve_execution_groups(rules)
    group_ids = [{rule.metadata.rule_id for rule in group} for group in groups]
    assert group_ids[0] == {"a-rule"}
    assert group_ids[1] == {"c-rule"}
    assert group_ids[2] == {"g-rule"}


def test_resolve_execution_groups_honors_explicit_dependency():
    rules = [
        _FakeRule("dependent-rule", rule_dependencies=["base-rule"]),
        _FakeRule("base-rule"),
    ]
    groups = resolve_execution_groups(rules)
    assert [rule.metadata.rule_id for rule in groups[0]] == ["base-rule"]
    assert [rule.metadata.rule_id for rule in groups[1]] == ["dependent-rule"]


def test_resolve_execution_groups_detects_cycles():
    rules = [
        _FakeRule("rule-a", rule_dependencies=["rule-b"]),
        _FakeRule("rule-b", rule_dependencies=["rule-a"]),
    ]
    try:
        resolve_execution_groups(rules)
        raised = False
    except CyclicRuleDependencyError:
        raised = True
    assert raised


def test_resolve_execution_groups_on_real_registry_covers_all_rules():
    registry = create_default_registry()
    rules = registry.select_rules(None)
    groups = resolve_execution_groups(rules)
    flattened = [rule.metadata.rule_id for group in groups for rule in group]
    assert set(flattened) == {rule.metadata.rule_id for rule in rules}
    assert len(flattened) == len(rules)
