from misra_platform_rules.analyzers.essential_type_engine import EssentialTypeEngine
from misra_platform_rules.ast_graph import AstGraph


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[dict] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"n{self._counter}"

    def node(self, kind: str, parent: str | None = None, **kwargs) -> str:
        node_id = self._next_id()
        line = len(self.nodes) + 1
        payload = {
            "node_id": node_id,
            "node_kind": kind,
            "parent_id": parent or "",
            "children_ids": [],
            "source_range": {"line_start": line, "line_end": line, "column_start": 1},
            "type_information": kwargs.pop("type_information", {}),
            "semantic_properties": kwargs.pop("semantic_properties", {}),
            "essential_type": kwargs.pop("essential_type", ""),
        }
        payload.update(kwargs)
        self.nodes.append(payload)
        if parent:
            next(n for n in self.nodes if n["node_id"] == parent)["children_ids"].append(node_id)
        return node_id

    def graph(self) -> AstGraph:
        return AstGraph(self.nodes)


def test_promotion_of_small_types_to_signed_int():
    engine = EssentialTypeEngine()
    assert engine.promote("signed_char") == "signed_int"
    assert engine.promote("unsigned_short") == "signed_int"
    assert engine.promote("boolean") == "signed_int"


def test_promotion_leaves_int_and_wider_unchanged():
    engine = EssentialTypeEngine()
    assert engine.promote("signed_int") == "signed_int"
    assert engine.promote("unsigned_long") == "unsigned_long"
    assert engine.promote("double") == "double"


def test_uac_same_category_picks_higher_rank():
    engine = EssentialTypeEngine()
    assert engine.usual_arithmetic_conversion("signed_int", "signed_long") == "signed_long"


def test_uac_mixed_signedness_unsigned_wins_when_rank_gte():
    engine = EssentialTypeEngine()
    assert engine.usual_arithmetic_conversion("signed_int", "unsigned_int") == "unsigned_int"


def test_uac_mixed_signedness_signed_wins_when_wider():
    engine = EssentialTypeEngine()
    assert engine.usual_arithmetic_conversion("signed_long", "unsigned_char") == "signed_long"


def test_uac_promotes_small_types_before_combining():
    engine = EssentialTypeEngine()
    # signed_char and unsigned_char both promote to signed_int first, so the
    # result is signed_int, not the (incorrect, un-promoted) unsigned_char.
    assert engine.usual_arithmetic_conversion("signed_char", "unsigned_char") == "signed_int"


def test_uac_float_wins_over_integer():
    engine = EssentialTypeEngine()
    assert engine.usual_arithmetic_conversion("signed_int", "float") == "float"
    assert engine.usual_arithmetic_conversion("double", "float") == "double"


def test_enum_essential_type_is_distinct_per_enum():
    engine = EssentialTypeEngine()
    color = engine.enum_essential_type("Color")
    shape = engine.enum_essential_type("Shape")
    assert engine.is_enum_type(color)
    assert color != shape
    assert engine.enum_name(color) == "Color"
    assert engine.is_inappropriate_operand_pair(color, shape)
    assert not engine.is_inappropriate_operand_pair(color, color)


def test_enum_mixed_with_plain_integer_is_inappropriate():
    engine = EssentialTypeEngine()
    color = engine.enum_essential_type("Color")
    assert engine.is_inappropriate_operand_pair(color, "signed_int")


def test_bitfield_essential_type_by_width():
    engine = EssentialTypeEngine()
    assert engine.bitfield_essential_type(is_signed=True, bit_width=1) == "boolean"
    assert engine.bitfield_essential_type(is_signed=False, bit_width=3) == "unsigned_char"
    assert engine.bitfield_essential_type(is_signed=True, bit_width=10) == "signed_short"
    assert engine.bitfield_essential_type(is_signed=False, bit_width=32) == "unsigned_int"


def test_literal_essential_type_picks_smallest_fitting_signed_type():
    b = _Builder()
    literal = b.node("IntegerLiteral", semantic_properties={"value": "5"})
    engine = EssentialTypeEngine()
    result = engine.essential_type_of_expression(b.graph().get(literal), b.graph())
    assert result == "signed_char"


def test_literal_essential_type_respects_unsigned_suffix():
    b = _Builder()
    literal = b.node("IntegerLiteral", semantic_properties={"value": "5u"})
    engine = EssentialTypeEngine()
    result = engine.essential_type_of_expression(b.graph().get(literal), b.graph())
    assert result == "unsigned_char"


def test_relational_operator_essential_type_is_boolean():
    b = _Builder()
    op = b.node("BinaryOperator", semantic_properties={"opcode": "=="})
    b.node("IntegerLiteral", parent=op, semantic_properties={"value": "1"})
    b.node("IntegerLiteral", parent=op, semantic_properties={"value": "2"})
    engine = EssentialTypeEngine()
    graph = b.graph()
    assert engine.essential_type_of_expression(graph.get(op), graph) == "boolean"


def test_shift_operator_uses_only_left_operand_promoted_type():
    b = _Builder()
    op = b.node("BinaryOperator", semantic_properties={"opcode": "<<"})
    b.node("IntegerLiteral", parent=op, essential_type="signed_char", semantic_properties={"value": "1"})
    b.node("IntegerLiteral", parent=op, essential_type="unsigned_long", semantic_properties={"value": "40"})
    engine = EssentialTypeEngine()
    graph = b.graph()
    # left operand (signed_char, essential_type overridden) promotes to signed_int
    # regardless of the right operand's much wider type.
    result = engine.essential_type_of_expression(op_node := graph.get(op), graph)
    _ = op_node
    assert result == "signed_int"


def test_explicit_cast_resets_essential_type():
    b = _Builder()
    cast = b.node(
        "CStyleCastExpr", type_information={"fundamental_kind": "unsigned_char"},
        essential_type="unsigned_char",
    )
    inner = b.node("IntegerLiteral", parent=cast, semantic_properties={"value": "1000"})
    _ = inner
    engine = EssentialTypeEngine()
    graph = b.graph()
    assert engine.essential_type_of_expression(graph.get(cast), graph) == "unsigned_char"


def test_conditional_operator_same_category_picks_higher_rank():
    b = _Builder()
    ternary = b.node("ConditionalOperator")
    b.node("IntegerLiteral", parent=ternary, semantic_properties={"value": "1"})  # condition
    b.node("IntegerLiteral", parent=ternary, essential_type="signed_int", semantic_properties={"value": "1"})
    b.node("IntegerLiteral", parent=ternary, essential_type="signed_long", semantic_properties={"value": "1"})
    engine = EssentialTypeEngine()
    graph = b.graph()
    result = engine.essential_type_of_expression(graph.get(ternary), graph)
    assert result == "signed_long"


def test_unary_not_is_boolean_and_unary_minus_promotes():
    b = _Builder()
    not_op = b.node("UnaryOperator", semantic_properties={"opcode": "!"})
    b.node("IntegerLiteral", parent=not_op, semantic_properties={"value": "1"})

    minus_op = b.node("UnaryOperator", semantic_properties={"opcode": "-"})
    b.node("IntegerLiteral", parent=minus_op, essential_type="signed_char", semantic_properties={"value": "1"})

    engine = EssentialTypeEngine()
    graph = b.graph()
    assert engine.essential_type_of_expression(graph.get(not_op), graph) == "boolean"
    assert engine.essential_type_of_expression(graph.get(minus_op), graph) == "signed_int"
