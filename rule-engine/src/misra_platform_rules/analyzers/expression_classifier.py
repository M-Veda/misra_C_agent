"""Shared infrastructure for the Expressions pack: classify expression nodes
without duplicating AST-walk logic in every rule."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_LITERAL_KINDS = {"IntegerLiteral", "FloatingLiteral", "CharacterLiteral", "StringLiteral"}
_CONDITION_PARENT_KINDS = {"IfStmt", "WhileStmt", "DoStmt", "ForStmt"}
_ASSIGNMENT_OPCODES = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}


class ExpressionClassifier:
    def essential_type_of(self, node: dict[str, Any]) -> str:
        return node.get("essential_type", "unknown")

    def is_literal(self, node: dict[str, Any]) -> bool:
        return node.get("node_kind") in _LITERAL_KINDS

    def is_constant_expression(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        if self.is_literal(node):
            return True
        if node.get("node_kind") in ("BinaryOperator", "UnaryOperator", "ParenExpr"):
            children = graph.children(node["node_id"])
            return bool(children) and all(self.is_constant_expression(c, graph) for c in children)
        return False

    def has_side_effects(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        if node.get("node_kind") == "CallExpr":
            return True
        opcode = node.get("semantic_properties", {}).get("opcode", "")
        if opcode in _ASSIGNMENT_OPCODES or opcode in ("++", "--"):
            return True
        return any(self.has_side_effects(child, graph) for child in graph.children(node["node_id"]))

    def is_condition_of_control_statement(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        parent = graph.get(node.get("parent_id", ""))
        if not parent or parent.get("node_kind") not in _CONDITION_PARENT_KINDS:
            return False
        children = graph.children(parent["node_id"])
        if not children:
            return False
        # DoStmt serializes children as [body, cond]; every other control
        # statement serializes [cond, ...]. Approximate accordingly.
        condition_index = -1 if parent.get("node_kind") == "DoStmt" else 0
        return children[condition_index].get("node_id") == node.get("node_id")

    def is_assignment_used_as_condition(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        if node.get("node_kind") != "BinaryOperator":
            return False
        opcode = node.get("semantic_properties", {}).get("opcode", "")
        if opcode not in _ASSIGNMENT_OPCODES:
            return False
        return self.is_condition_of_control_statement(node, graph)

    def uses_comma_operator(self, node: dict[str, Any]) -> bool:
        return node.get("node_kind") == "BinaryOperator" and node.get("semantic_properties", {}).get(
            "opcode"
        ) == ","

    def is_essentially_boolean_context_mismatch(self, node: dict[str, Any], graph: "AstGraph") -> bool:
        """A control-statement condition whose essential type is not boolean."""
        if not self.is_condition_of_control_statement(node, graph):
            return False
        return self.essential_type_of(node) not in ("boolean", "unknown")
