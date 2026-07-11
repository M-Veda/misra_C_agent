from typing import Protocol

from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix


class IRulePlugin(Protocol):
    @property
    def metadata(self) -> RuleMetadata: ...

    def detect(self, context: RuleContext) -> list[RuleResult]: ...

    def explain(self, result: RuleResult) -> str: ...

    def generate_fix(self, result: RuleResult) -> SuggestedFix | None: ...

    def examples(self) -> RuleExamples: ...
