"""Category B (type-system) shared infrastructure: MISRA essential type model."""

from typing import Any

_RANK_ORDER = [
    "boolean",
    "signed_char",
    "unsigned_char",
    "char",
    "signed_short",
    "unsigned_short",
    "signed_int",
    "unsigned_int",
    "signed_long",
    "unsigned_long",
    "signed_long_long",
    "unsigned_long_long",
    "float",
    "double",
    "long_double",
    "complex",
    "unknown",
]

_CATEGORY_BY_TYPE = {
    "boolean": "boolean",
    "signed_char": "signed",
    "signed_short": "signed",
    "signed_int": "signed",
    "signed_long": "signed",
    "signed_long_long": "signed",
    "unsigned_char": "unsigned",
    "unsigned_short": "unsigned",
    "unsigned_int": "unsigned",
    "unsigned_long": "unsigned",
    "unsigned_long_long": "unsigned",
    "char": "character",
    "float": "floating",
    "double": "floating",
    "long_double": "floating",
    "complex": "complex",
    "unknown": "unknown",
}

# Essential-type category pairs that MISRA C:2012 Rule 10.1/10.4 forbid in a
# binary/arithmetic operation without an explicit, intentional cast.
_INAPPROPRIATE_OPERAND_PAIRS: set[tuple[str, str]] = {
    ("boolean", "signed_char"),
    ("boolean", "unsigned_char"),
    ("boolean", "signed_short"),
    ("boolean", "unsigned_short"),
    ("boolean", "signed_int"),
    ("boolean", "unsigned_int"),
    ("boolean", "signed_long"),
    ("boolean", "unsigned_long"),
    ("boolean", "float"),
    ("boolean", "double"),
    ("signed_char", "unsigned_char"),
    ("signed_short", "unsigned_short"),
    ("signed_int", "unsigned_int"),
    ("signed_long", "unsigned_long"),
    ("signed_long_long", "unsigned_long_long"),
}


class EssentialTypeAnalyzer:
    """Essential-type classification, ranking, and conversion-appropriateness."""

    def rank(self, essential_type: str) -> int:
        try:
            return _RANK_ORDER.index(essential_type)
        except ValueError:
            return len(_RANK_ORDER)

    def category(self, essential_type: str) -> str:
        return _CATEGORY_BY_TYPE.get(essential_type, "unknown")

    def is_signed(self, essential_type: str) -> bool:
        return self.category(essential_type) == "signed"

    def is_unsigned(self, essential_type: str) -> bool:
        return self.category(essential_type) == "unsigned"

    def is_floating(self, essential_type: str) -> bool:
        return self.category(essential_type) == "floating"

    def is_boolean(self, essential_type: str) -> bool:
        return essential_type == "boolean"

    def is_narrowing(self, from_type: str, to_type: str) -> bool:
        """True if assigning/converting from_type -> to_type may lose information."""
        if from_type in ("unknown", "complex") or to_type in ("unknown", "complex"):
            return False
        if self.category(from_type) == self.category(to_type):
            return self.rank(from_type) > self.rank(to_type)
        # Cross-category narrowing: floating -> integer, signed -> unsigned of
        # equal-or-smaller rank, or any type -> boolean.
        if self.is_floating(from_type) and not self.is_floating(to_type):
            return True
        if self.is_signed(from_type) and self.is_unsigned(to_type):
            return self.rank(from_type) >= self.rank(to_type)
        return self.rank(from_type) > self.rank(to_type)

    def is_inappropriate_operand_pair(self, left: str, right: str) -> bool:
        return (left, right) in _INAPPROPRIATE_OPERAND_PAIRS or (
            right,
            left,
        ) in _INAPPROPRIATE_OPERAND_PAIRS

    def essential_type_of(self, node: dict[str, Any]) -> str:
        return node.get("essential_type", "unknown")
