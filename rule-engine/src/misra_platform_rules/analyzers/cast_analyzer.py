"""Category B shared infrastructure: explicit/implicit cast analysis."""

from typing import Any

from misra_platform_rules.analyzers.essential_type_analyzer import EssentialTypeAnalyzer

_CAST_NODE_KINDS = {"CStyleCastExpr", "ImplicitCastExpr", "CXXStaticCastExpr", "CXXReinterpretCastExpr"}


class CastAnalyzer:
    def __init__(self, essential_types: EssentialTypeAnalyzer | None = None) -> None:
        self.essential_types = essential_types or EssentialTypeAnalyzer()

    def is_cast(self, node: dict[str, Any]) -> bool:
        return node.get("node_kind") in _CAST_NODE_KINDS

    def is_explicit_cast(self, node: dict[str, Any]) -> bool:
        return node.get("node_kind") == "CStyleCastExpr"

    def is_implicit_cast(self, node: dict[str, Any]) -> bool:
        return node.get("node_kind") == "ImplicitCastExpr"

    def removed_qualifiers(self, node: dict[str, Any]) -> list[str]:
        props = node.get("semantic_properties", {})
        if not props.get("removes_qualifier", False):
            return []
        return list(props.get("removed_qualifiers", []))

    def narrows(self, node: dict[str, Any], operand: dict[str, Any]) -> bool:
        target = node.get("essential_type", "unknown")
        source = operand.get("essential_type", "unknown")
        return self.essential_types.is_narrowing(source, target)

    def changes_pointer_type(self, node: dict[str, Any], operand: dict[str, Any]) -> bool:
        target_type = node.get("type_information", {})
        source_type = operand.get("type_information", {})
        if not target_type.get("is_pointer") or not source_type.get("is_pointer"):
            return False
        return target_type.get("pointee_type") != source_type.get("pointee_type")

    def is_function_pointer_cast(self, node: dict[str, Any], operand: dict[str, Any]) -> bool:
        target_spelling = node.get("type_information", {}).get("spelling", "")
        source_spelling = operand.get("type_information", {}).get("spelling", "")
        return (
            "(" in target_spelling
            and "(" in source_spelling
            and target_spelling != source_spelling
        )
