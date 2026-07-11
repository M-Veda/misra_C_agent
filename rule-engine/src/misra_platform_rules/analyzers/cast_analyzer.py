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

    def is_composite_expression(self, node: dict[str, Any]) -> bool:
        return bool(node.get("semantic_properties", {}).get("is_composite_expression", False))

    def changes_object_pointer_type(self, node: dict[str, Any], operand: dict[str, Any]) -> bool:
        """Pointer-to-object cast where the pointee type changes (excludes void*)."""
        if not self.changes_pointer_type(node, operand):
            return False
        void_pointees = {"void", "const void", ""}
        target_pointee = node.get("type_information", {}).get("pointee_type", "")
        source_pointee = operand.get("type_information", {}).get("pointee_type", "")
        if target_pointee in void_pointees or source_pointee in void_pointees:
            return False
        target_spelling = node.get("type_information", {}).get("spelling", "")
        source_spelling = operand.get("type_information", {}).get("spelling", "")
        if "(" in target_spelling or "(" in source_spelling:
            return False
        return True

    def casts_pointer_to_non_integer_arithmetic(
        self, node: dict[str, Any], operand: dict[str, Any]
    ) -> bool:
        """Pointer operand cast to a non-integer arithmetic essential type."""
        if not operand.get("type_information", {}).get("is_pointer", False):
            return False
        target_type = node.get("essential_type", "unknown")
        return self.essential_types.is_floating(target_type)

    def changes_to_wider_category(self, node: dict[str, Any], operand: dict[str, Any]) -> bool:
        """Cast from a composite expression to a wider essential-type category."""
        target = node.get("essential_type", "unknown")
        source = operand.get("essential_type", "unknown")
        if target == "unknown" or source == "unknown":
            return False
        if self.essential_types.category(target) == self.essential_types.category(source):
            return False
        return self.essential_types.is_wider(source, target)
