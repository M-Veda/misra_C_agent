"""Category B shared infrastructure: pointer semantics analysis."""

from typing import Any

_ARITHMETIC_OPCODES = {"+", "-", "+=", "-=", "++", "--"}


class PointerAnalyzer:
    def is_pointer(self, node: dict[str, Any]) -> bool:
        return bool(node.get("type_information", {}).get("is_pointer", False))

    def is_null_constant(self, node: dict[str, Any]) -> bool:
        if node.get("node_kind") != "IntegerLiteral":
            return False
        value = node.get("semantic_properties", {}).get("value", "0")
        return str(value) in ("0", "0x0", "NULL")

    def is_pointer_arithmetic(self, node: dict[str, Any], operands: list[dict[str, Any]]) -> bool:
        opcode = node.get("semantic_properties", {}).get("opcode", "")
        if opcode not in _ARITHMETIC_OPCODES:
            return False
        return any(self.is_pointer(operand) for operand in operands)

    def is_two_pointer_subtraction(self, node: dict[str, Any], operands: list[dict[str, Any]]) -> bool:
        opcode = node.get("semantic_properties", {}).get("opcode", "")
        if opcode != "-" or len(operands) < 2:
            return False
        return self.is_pointer(operands[0]) and self.is_pointer(operands[1])

    def pointee_type(self, node: dict[str, Any]) -> str:
        return node.get("type_information", {}).get("pointee_type", "")

    def is_incompatible_pointer_assignment(
        self, lhs: dict[str, Any], rhs: dict[str, Any]
    ) -> bool:
        if not self.is_pointer(lhs) or not self.is_pointer(rhs):
            return False
        lhs_pointee = self.pointee_type(lhs)
        rhs_pointee = self.pointee_type(rhs)
        if not lhs_pointee or not rhs_pointee:
            return False
        if lhs_pointee in ("void", "const void") or rhs_pointee in ("void", "const void"):
            return False
        return lhs_pointee != rhs_pointee

    def returns_address_of_local(
        self, return_stmt: dict[str, Any], descendants: list[dict[str, Any]], local_names: set[str]
    ) -> str | None:
        for node in descendants:
            if node.get("node_kind") != "UnaryOperator":
                continue
            if node.get("semantic_properties", {}).get("opcode") != "&":
                continue
            for child in descendants:
                if child.get("parent_id") == node.get("node_id") and child.get("node_kind") == "DeclRefExpr":
                    name = child.get("semantic_properties", {}).get("name", "")
                    if name in local_names:
                        return name
        return None
