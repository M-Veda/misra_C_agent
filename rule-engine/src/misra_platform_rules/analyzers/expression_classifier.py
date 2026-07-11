"""Shared infrastructure for the Expressions pack: classify expression nodes
without duplicating AST-walk logic in every rule."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_LITERAL_KINDS = {"IntegerLiteral", "FloatingLiteral", "CharacterLiteral", "StringLiteral"}
_CONDITION_PARENT_KINDS = {"IfStmt", "WhileStmt", "DoStmt", "ForStmt"}
_ASSIGNMENT_OPCODES = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
_INC_DEC_OPCODES = {"++", "--"}
_SHIFT_OPCODES = {"<<", ">>"}
_FLOATING_ESSENTIAL_TYPES = {"float", "double", "long_double"}
_EXPRESSION_PARENT_KINDS = {
    "BinaryOperator",
    "UnaryOperator",
    "CallExpr",
    "CStyleCastExpr",
    "ConditionalOperator",
    "ArraySubscriptExpr",
    "MemberExpr",
    "ParenExpr",
    "InitListExpr",
    "ImplicitCastExpr",
}


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

    def is_increment_or_decrement(self, node: dict[str, Any]) -> bool:
        return (
            node.get("node_kind") == "UnaryOperator"
            and node.get("semantic_properties", {}).get("opcode") in _INC_DEC_OPCODES
        )

    def full_expression_root(self, node: dict[str, Any], graph: "AstGraph") -> dict[str, Any]:
        current = node
        while True:
            parent = graph.get(current.get("parent_id", ""))
            if not parent or parent.get("node_kind") not in _EXPRESSION_PARENT_KINDS:
                return current
            current = parent

    def has_other_side_effects_in_full_expression(
        self, inc_dec_node: dict[str, Any], graph: "AstGraph"
    ) -> bool:
        """MISRA Rule 13.3: the full expression also contains side effects beyond ++/--."""
        root = self.full_expression_root(inc_dec_node, graph)
        if root["node_id"] == inc_dec_node["node_id"]:
            return False

        def _walk(node: dict[str, Any]) -> bool:
            if node["node_id"] == inc_dec_node["node_id"]:
                return False
            if node.get("node_kind") == "CallExpr":
                return True
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            if opcode in _ASSIGNMENT_OPCODES or opcode in _INC_DEC_OPCODES:
                return True
            return any(_walk(child) for child in graph.children(node["node_id"]))

        return _walk(root)

    def shift_amount_out_of_range(self, node: dict[str, Any]) -> bool:
        opcode = node.get("semantic_properties", {}).get("opcode", "")
        if opcode not in _SHIFT_OPCODES:
            return False
        props = node.get("semantic_properties", {})
        amount = props.get("shift_amount")
        width = props.get("shift_width")
        if amount is None or width is None:
            return False
        return amount < 0 or amount >= width

    def wraps_on_constant_unsigned(self, node: dict[str, Any]) -> bool:
        if not node.get("semantic_properties", {}).get("wraps_on_evaluation", False):
            return False
        essential = self.essential_type_of(node)
        if essential.startswith("unsigned"):
            return True
        return bool(node.get("semantic_properties", {}).get("is_constant_unsigned", False))

    def loop_counter_is_floating(self, for_node: dict[str, Any], graph: "AstGraph") -> bool:
        props = for_node.get("semantic_properties", {})
        counter_type = props.get("loop_counter_essential_type")
        if counter_type in _FLOATING_ESSENTIAL_TYPES:
            return True
        for child in graph.children(for_node["node_id"]):
            if child.get("node_kind") != "VarDecl":
                continue
            if self.essential_type_of(child) in _FLOATING_ESSENTIAL_TYPES:
                return True
        return False

    def switch_condition_is_boolean(self, switch_node: dict[str, Any], graph: "AstGraph") -> bool:
        children = graph.children(switch_node["node_id"])
        if not children:
            return False
        return self.essential_type_of(children[0]) == "boolean"

    def has_undefined_behaviour(self, node: dict[str, Any]) -> bool:
        return bool(node.get("semantic_properties", {}).get("undefined_behaviour"))

    def has_unordered_evaluation(self, node: dict[str, Any]) -> bool:
        return bool(node.get("semantic_properties", {}).get("unordered_evaluation"))

    def controlling_expression_invariant(self, stmt_node: dict[str, Any], graph: "AstGraph") -> bool:
        if stmt_node.get("semantic_properties", {}).get("controlling_expression_invariant"):
            return True
        if stmt_node.get("node_kind") not in _CONDITION_PARENT_KINDS:
            return False
        children = graph.children(stmt_node["node_id"])
        if not children:
            return False
        condition_index = -1 if stmt_node.get("node_kind") == "DoStmt" else 0
        condition = children[condition_index]
        return bool(condition.get("semantic_properties", {}).get("controlling_expression_invariant"))

    def is_discarded_non_void_call(self, call_node: dict[str, Any], graph: "AstGraph") -> bool:
        """MISRA Rule 17.7: a non-void call used only as a standalone statement."""
        props = call_node.get("semantic_properties", {})
        if props.get("return_type") == "void" or props.get("has_non_void_return") is False:
            return False
        if not props.get("has_non_void_return") and not props.get("return_type"):
            return False

        parent = graph.get(call_node.get("parent_id", ""))
        if not parent:
            return False

        parent_kind = parent.get("node_kind")
        if parent_kind == "CStyleCastExpr" and parent.get("semantic_properties", {}).get("cast_to_void"):
            return False
        if parent_kind == "BinaryOperator" and parent.get("semantic_properties", {}).get("opcode") in _ASSIGNMENT_OPCODES:
            return False
        if parent_kind in ("VarDecl", "ReturnStmt"):
            return False
        if parent_kind in ("CompoundStmt", "ExprStmt"):
            return True
        return False
