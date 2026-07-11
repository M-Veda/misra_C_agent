"""MISRA C:2012 Rule 8.4 — compatible declaration visible for external linkage definitions.

Phase 3 upgrade: in addition to the single-TU "no prior declaration" check
from Phase 1.2, this rule now also consults `LinkageIndex`
(`context.cross_tu_linkage`) when available to flag a genuinely cross-TU
signal: the same external identifier declared with incompatible type
spellings in different translation units. This promotes the rule from
Category A to Category E for that check while remaining backward compatible
when no project-wide linkage index has been built (e.g. in isolated tests).
"""

from misra_platform_rules.enums import RuleCategory, RuleSeverity, RuleStandard
from misra_platform_rules.rule_base import BaseRulePlugin
from misra_platform_rules.rule_context import RuleContext
from misra_platform_rules.rule_result import RuleExamples, RuleMetadata, RuleResult, SuggestedFix
from misra_platform_rules.taxonomy import RuleImplementationCategory, RulePack


class Rule8_4(BaseRulePlugin):
    @property
    def metadata(self) -> RuleMetadata:
        return RuleMetadata(
            rule_id="misra-c2012-rule-8-4",
            rule_number="8.4",
            standard=RuleStandard.MISRA_C_2012,
            category=RuleCategory.REQUIRED,
            severity=RuleSeverity.MAJOR,
            title="Compatible declaration visible when an entity with external linkage is defined",
            description=(
                "If an object or function with external linkage is defined, a compatible "
                "declaration shall be visible."
            ),
            rationale=(
                "External linkage definitions without a visible compatible declaration can "
                "lead to incompatible type assumptions across translation units."
            ),
            tags=["linkage", "declarations", "cross-tu"],
            references=["MISRA C:2012 Rule 8.4"],
            plugin_module="misra_platform_rules.standards.misra_c_2012.rules.rule_8_4",
            requires_ast_nodes=["FunctionDecl", "VarDecl"],
            implementation_category=RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT,
            rule_pack=RulePack.LINKAGE,
            requires_linkage=True,
        )

    def detect(self, context: RuleContext) -> list[RuleResult]:
        graph = self.graph(context)
        results: list[RuleResult] = []
        declarations: dict[str, list[dict]] = {}

        for node in graph.nodes_by_kind("FunctionDecl"):
            name = node.get("semantic_properties", {}).get("name", "")
            if name:
                declarations.setdefault(name, []).append(node)

        for node in graph.nodes_by_kind("VarDecl"):
            name = node.get("semantic_properties", {}).get("name", "")
            if name:
                declarations.setdefault(name, []).append(node)

        for name, nodes in declarations.items():
            if not graph.is_file_scope(nodes[-1]["node_id"]):
                continue
            storage = nodes[-1].get("semantic_properties", {}).get("storage_class", "external")
            if storage == "static":
                continue
            has_body = any(child.get("node_kind") == "CompoundStmt" for child in graph.children(nodes[-1]["node_id"]))
            if not has_body and len(nodes) == 1:
                continue
            if len(nodes) == 1 and has_body:
                results.append(
                    self.make_result(
                        context,
                        graph,
                        nodes[0],
                        explanation=(
                            f"External linkage definition of '{name}' has no prior compatible "
                            "declaration in this translation unit."
                        ),
                        risk_description="Cross-TU type mismatches may remain undetected until link time.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.7,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.2,
                            "fix_generator_certainty": 0.6,
                        },
                        confidence_score=0.82,
                        suggested_fix=SuggestedFix(
                            original_code=f"definition of {name}",
                            suggested_code=f"extern declaration for {name} before definition",
                            rationale="Provide a visible compatible declaration before the definition.",
                            confidence_score=0.6,
                        ),
                    )
                )

        linkage = self.linkage(context)
        if linkage.data.get("symbols"):
            already_flagged = {result.offending_expression for result in results}
            for name in linkage.all_names():
                if not linkage.incompatible_type_spellings(name):
                    continue
                node = declarations.get(name, [None])[-1]
                if node is None:
                    continue
                offending = f"{node.get('node_kind', '')} {name}"
                if offending in already_flagged:
                    continue
                results.append(
                    self.make_result(
                        context,
                        graph,
                        node,
                        explanation=(
                            f"'{name}' has external linkage but incompatible declared types "
                            "across translation units."
                        ),
                        risk_description="Incompatible cross-TU declarations are undefined behaviour at link time.",
                        confidence_factors={
                            "ast_match_specificity": 0.85,
                            "type_information_complete": 0.75,
                            "macro_clarity": 0.9,
                            "historical_false_positive_rate": 0.15,
                            "fix_generator_certainty": 0.3,
                        },
                        confidence_score=0.8,
                        suggested_fix=None,
                    )
                )
        return results

    def examples(self) -> RuleExamples:
        return RuleExamples(
            compliant=["extern uint16_t counter;\nuint16_t counter = 0U;"],
            non_compliant=["uint16_t counter = 0U; /* no prior declaration */"],
        )
