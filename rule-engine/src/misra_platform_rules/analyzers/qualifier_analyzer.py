"""Category B shared infrastructure: const/volatile/restrict qualifier tracking."""

from typing import Any


class QualifierAnalyzer:
    def qualifiers(self, node: dict[str, Any]) -> list[str]:
        return list(node.get("qualifiers", []))

    def has_qualifier(self, node: dict[str, Any], qualifier: str) -> bool:
        return qualifier in self.qualifiers(node)

    def is_const(self, node: dict[str, Any]) -> bool:
        return self.has_qualifier(node, "const")

    def is_volatile(self, node: dict[str, Any]) -> bool:
        return self.has_qualifier(node, "volatile")

    def lost_qualifiers(self, source: dict[str, Any], target: dict[str, Any]) -> list[str]:
        """Qualifiers present on `source` but absent on `target`."""
        return [q for q in self.qualifiers(source) if q not in self.qualifiers(target)]

    def assignment_drops_qualifier(self, lhs: dict[str, Any], rhs: dict[str, Any]) -> list[str]:
        return self.lost_qualifiers(rhs, lhs)
