"""Phase 4: Essential Type Engine v2 — the parts of the MISRA C:2012 Amd 2
essential type model that Phase 3's `EssentialTypeAnalyzer` deliberately left
out (it only covered rank/category/narrowing/inappropriate-pairs for
*already-computed* leaf essential types):

  - integer promotion (the "usual unary conversion" C performs before *any*
    arithmetic/relational operator is applied)
  - usual arithmetic conversions (UAC) between two promoted operand types
  - enum essential types (each enum is its own essential-type category,
    distinct from any other enum and from plain integers, per MISRA)
  - bit-field essential types (derived from declared width + signedness,
    not just the field's declared base type)
  - bottom-up essential type inference over a *composite expression tree*
    (literals, casts, unary/binary/ternary operators), which is what most
    real MISRA Rule 10.x violations actually hinge on — Phase 3 rules only
    read `node["essential_type"]` off individual nodes as annotated by
    clang-worker; this reconstructs it for expressions that need it derived.

Reuses `EssentialTypeAnalyzer` (Phase 3) for rank/category tables rather
than duplicating them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from misra_platform_rules.analyzers.essential_type_analyzer import EssentialTypeAnalyzer

if TYPE_CHECKING:
    from misra_platform_rules.ast_graph import AstGraph

_RELATIONAL_OPCODES = {"==", "!=", "<", ">", "<=", ">=", "&&", "||"}
_SHIFT_OPCODES = {"<<", ">>"}
_ARITHMETIC_OPCODES = {"+", "-", "*", "/", "%", "&", "|", "^"}

# Smallest signed/unsigned essential type whose value range covers a given
# bit-field width, per the essential type model (Appendix D / Amd 2 table).
_BITFIELD_SIGNED_BY_WIDTH = [
    (1, "boolean"),
    (8, "signed_char"),
    (16, "signed_short"),
    (32, "signed_int"),
    (64, "signed_long_long"),
]
_BITFIELD_UNSIGNED_BY_WIDTH = [
    (1, "boolean"),
    (8, "unsigned_char"),
    (16, "unsigned_short"),
    (32, "unsigned_int"),
    (64, "unsigned_long_long"),
]


class EssentialTypeEngine:
    def __init__(self) -> None:
        self._base = EssentialTypeAnalyzer()

    # ------------------------------------------------------------------
    # Integer promotion / usual arithmetic conversions
    # ------------------------------------------------------------------

    def promote(self, essential_type: str, *, int_bit_width: int = 32) -> str:
        """The "integer promotion" step C performs on any operand of rank
        lower than `int` before it takes part in an operator. Every type
        with strictly-lower-than-`signed_int` rank promotes to `signed_int`
        if `int` can represent its whole range, else to `unsigned_int` — on
        every mainstream MISRA target (`int` >= 16 bits, `char`/`short`
        narrower than `int`), that condition always holds, so the common
        case is a flat "promotes to signed_int". Enum essential types
        promote using their underlying integer type's rank."""
        if self.is_enum_type(essential_type):
            underlying = self.enum_underlying_type(essential_type)
            return self.promote(underlying, int_bit_width=int_bit_width)

        if essential_type in ("unknown", "complex"):
            return essential_type

        int_rank = self._base.rank("signed_int")
        if self._base.rank(essential_type) >= int_rank:
            return essential_type  # already int-or-wider: no promotion
        return "signed_int"

    def usual_arithmetic_conversion(self, left: str, right: str) -> str:
        """UAC of two *already-promoted* operand essential types, applied
        automatically here (callers may pass raw operand types directly).
        Mirrors the standard C ranking: same category -> higher rank wins;
        mixed signed/unsigned -> the unsigned type wins if its rank is >=
        the signed type's rank, otherwise the signed type wins (assuming a
        same-size signed type can represent the unsigned type's range,
        which holds for the fixed-width categories modeled here)."""
        left_p = self.promote(left)
        right_p = self.promote(right)

        if left_p in ("unknown", "complex") or right_p in ("unknown", "complex"):
            return "unknown"

        if self._base.is_floating(left_p) or self._base.is_floating(right_p):
            # Float always wins UAC against an integer type regardless of
            # rank; between two floats, the wider one wins.
            floating_candidates = [t for t in (left_p, right_p) if self._base.is_floating(t)]
            return max(floating_candidates, key=self._base.rank)

        if left_p == right_p:
            return left_p

        left_signed = self._base.is_signed(left_p)
        right_signed = self._base.is_signed(right_p)
        if left_signed == right_signed:
            return max(left_p, right_p, key=self._base.rank)

        signed_type = left_p if left_signed else right_p
        unsigned_type = right_p if left_signed else left_p
        if self._base.rank(unsigned_type) >= self._base.rank(signed_type):
            return unsigned_type
        return signed_type

    # ------------------------------------------------------------------
    # Enum essential types
    # ------------------------------------------------------------------

    def enum_essential_type(self, enum_name: str) -> str:
        """Each named enum is its own distinct essential-type category —
        `enum<Foo>` is neither `enum<Bar>` nor any plain integer type for
        Rule 10.x "appropriate essential type" purposes, even though all
        three may share the same underlying representation."""
        return f"enum<{enum_name}>"

    def is_enum_type(self, essential_type: str) -> bool:
        return essential_type.startswith("enum<") and essential_type.endswith(">")

    def enum_name(self, essential_type: str) -> str:
        if not self.is_enum_type(essential_type):
            return ""
        return essential_type[len("enum<") : -1]

    def enum_underlying_type(self, essential_type: str, *, default: str = "signed_int") -> str:
        """Best-effort underlying integer type for an enum essential type.
        The serialized AST doesn't currently carry the enum's fixed
        underlying type separately, so this defaults to `signed_int`
        (matching typical C enum implementation) unless a caller-supplied
        override table says otherwise — see `enum_underlying_types` param
        on `essential_type_of_expression` for how rules can supply real
        per-enum underlying types discovered from the AST."""
        return default

    def is_inappropriate_operand_pair(self, left: str, right: str) -> bool:
        """Extends Phase 3's fixed-pair table with the enum-specific MISRA
        rule: two *different* enum essential types (or an enum mixed with
        any plain arithmetic type) are never an "appropriate" pair, even
        though Phase 3's table has no entries for enums at all."""
        if self.is_enum_type(left) or self.is_enum_type(right):
            if self.is_enum_type(left) and self.is_enum_type(right):
                return self.enum_name(left) != self.enum_name(right)
            return True
        return self._base.is_inappropriate_operand_pair(left, right)

    # ------------------------------------------------------------------
    # Bit-fields
    # ------------------------------------------------------------------

    def bitfield_essential_type(self, *, is_signed: bool, bit_width: int) -> str:
        table = _BITFIELD_SIGNED_BY_WIDTH if is_signed else _BITFIELD_UNSIGNED_BY_WIDTH
        for max_width, essential_type in table:
            if bit_width <= max_width:
                return essential_type
        return table[-1][1]

    # ------------------------------------------------------------------
    # Composite expression essential type inference
    # ------------------------------------------------------------------

    def essential_type_of_expression(
        self,
        node: dict[str, Any],
        graph: "AstGraph",
        *,
        enum_underlying_types: dict[str, str] | None = None,
    ) -> str:
        """Bottom-up essential type of an arbitrary expression subtree.
        Falls back to the node's own annotated `essential_type` (set by
        clang-worker on leaves) whenever the node kind isn't one of the
        composite forms this engine derives explicitly."""
        kind = node.get("node_kind")

        if kind in ("CStyleCastExpr", "ExplicitCastExpr", "CastExpr"):
            # An explicit cast is exactly how MISRA expects a developer to
            # assert a *new* essential type — it does not inherit the
            # operand's essential type at all.
            cast_type = node.get("type_information", {}).get("fundamental_kind", "")
            return cast_type or node.get("essential_type", "unknown")

        if kind == "IntegerLiteral":
            return node.get("essential_type") or self._literal_essential_type(node)

        if kind == "UnaryOperator":
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            children = graph.children(node["node_id"])
            if not children:
                return node.get("essential_type", "unknown")
            operand_type = self.essential_type_of_expression(
                children[0], graph, enum_underlying_types=enum_underlying_types
            )
            if opcode == "!":
                return "boolean"
            if opcode in ("-", "~", "+", "++", "--"):
                return self.promote(operand_type)
            return operand_type

        if kind == "BinaryOperator":
            opcode = node.get("semantic_properties", {}).get("opcode", "")
            children = graph.children(node["node_id"])
            if len(children) < 2:
                return node.get("essential_type", "unknown")
            left_type = self.essential_type_of_expression(
                children[0], graph, enum_underlying_types=enum_underlying_types
            )
            right_type = self.essential_type_of_expression(
                children[1], graph, enum_underlying_types=enum_underlying_types
            )
            if opcode in _RELATIONAL_OPCODES:
                return "boolean"
            if opcode in _SHIFT_OPCODES:
                # Shift result type is the promoted type of the LEFT operand
                # only — the right operand's type never participates in UAC.
                return self.promote(left_type)
            if opcode in _ARITHMETIC_OPCODES or opcode.endswith("="):
                return self.usual_arithmetic_conversion(left_type, right_type)
            return node.get("essential_type", "unknown")

        if kind == "ConditionalOperator":
            children = graph.children(node["node_id"])
            if len(children) < 3:
                return node.get("essential_type", "unknown")
            then_type = self.essential_type_of_expression(
                children[1], graph, enum_underlying_types=enum_underlying_types
            )
            else_type = self.essential_type_of_expression(
                children[2], graph, enum_underlying_types=enum_underlying_types
            )
            if then_type == else_type:
                return then_type
            if self._base.category(then_type) == self._base.category(else_type):
                return max(then_type, else_type, key=self._base.rank)
            return self.usual_arithmetic_conversion(then_type, else_type)

        return node.get("essential_type", "unknown")

    def _literal_essential_type(self, node: dict[str, Any]) -> str:
        """Smallest signed (or, with a `u`/`U` suffix, unsigned) type that
        can represent the literal's value — MISRA's rule for constant
        essential types, approximated with fixed-width ranges."""
        raw = str(node.get("semantic_properties", {}).get("value", "0"))
        is_unsigned = raw.lower().endswith(("u", "ul", "ull", "lu", "llu"))
        is_long = "l" in raw.lower()
        try:
            value = int(raw.rstrip("uUlL"), 0)
        except ValueError:
            return "unknown"

        if is_unsigned:
            candidates = [
                ("unsigned_char", 0xFF),
                ("unsigned_short", 0xFFFF),
                ("unsigned_int", 0xFFFFFFFF),
                ("unsigned_long", 0xFFFFFFFFFFFFFFFF),
                ("unsigned_long_long", 2**128 - 1),
            ]
        else:
            candidates = [
                ("signed_char", 0x7F),
                ("signed_short", 0x7FFF),
                ("signed_int", 0x7FFFFFFF),
                ("signed_long", 0x7FFFFFFFFFFFFFFF),
                ("signed_long_long", 2**127 - 1),
            ]
        start_index = 2 if is_long else 0
        for name, max_value in candidates[start_index:]:
            if value <= max_value:
                return name
        return candidates[-1][0]
