"""Category F shared infrastructure: preprocessor / macro table analysis.

Operates on `RuleContext.macro_table`, which mirrors
`clang_analysis.proto`'s `PreprocessorMetadata` (see
`ast_client.py::_preprocessor_to_dict`): `macro_definitions`,
`macro_expansions`, `include_directives`, `conditional_branches`. Unlike some
Category B rules, this data IS populated by the real clang-worker serializer
today, not just the Python-side test fixtures.
"""

import re
from typing import Any

_OPERATOR_PATTERN = re.compile(r"[+\-*/%&|^<>]")
_RESERVED_PREFIX_PATTERN = re.compile(r"^_[A-Z_]")


class MacroAnalyzer:
    def macro_definitions(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return macro_table.get("macro_definitions", [])

    def macro_expansions(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return macro_table.get("macro_expansions", [])

    def include_directives(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return macro_table.get("include_directives", [])

    def conditional_branches(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return macro_table.get("conditional_branches", [])

    def function_like_macros(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return [m for m in self.macro_definitions(macro_table) if m.get("is_function_like")]

    def object_like_macros(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return [m for m in self.macro_definitions(macro_table) if not m.get("is_function_like")]

    def is_reserved_identifier(self, name: str) -> bool:
        """MISRA Rule 21.1: identifiers reserved by the standard library
        (leading underscore + uppercase, or a double leading underscore)."""
        return bool(_RESERVED_PREFIX_PATTERN.match(name)) or name.startswith("__")

    def has_unparenthesized_operator_body(self, macro_def: dict[str, Any]) -> bool:
        """Heuristic for Rule 20.7: a function-like macro body containing a
        binary operator that is not fully wrapped in a single parenthesis
        pair risks operator-precedence bugs at the call site."""
        value = macro_def.get("value", "").strip()
        if not value or not _OPERATOR_PATTERN.search(value):
            return False
        if value.startswith("(") and value.endswith(")"):
            return False
        return True

    def expansions_of(self, macro_table: dict[str, Any], name: str) -> list[dict[str, Any]]:
        return [e for e in self.macro_expansions(macro_table) if e.get("name") == name]

    def unbalanced_conditional_group(self, macro_table: dict[str, Any]) -> bool:
        opens = sum(
            1
            for branch in self.conditional_branches(macro_table)
            if branch.get("directive") in ("if", "ifdef", "ifndef")
        )
        closes = sum(
            1 for branch in self.conditional_branches(macro_table) if branch.get("directive") == "endif"
        )
        return opens != closes

    def duplicate_macro_names_within(
        self, macro_table: dict[str, Any], significant_chars: int
    ) -> list[tuple[str, str]]:
        """Pairs of distinct macro names that collide within the first
        `significant_chars` characters — MISRA Rule 5.4 style checks."""
        truncated: dict[str, list[str]] = {}
        for macro_def in self.macro_definitions(macro_table):
            name = macro_def.get("name", "")
            if not name:
                continue
            key = name[:significant_chars]
            truncated.setdefault(key, []).append(name)

        collisions: list[tuple[str, str]] = []
        for names in truncated.values():
            unique = sorted(set(names))
            if len(unique) > 1:
                for i, first in enumerate(unique):
                    for second in unique[i + 1 :]:
                        collisions.append((first, second))
        return collisions

    def is_unused(self, macro_table: dict[str, Any], macro_def: dict[str, Any]) -> bool:
        """MISRA Rule 2.5: a macro that is never expanded anywhere in the
        translation unit."""
        return not self.expansions_of(macro_table, macro_def.get("name", ""))

    def non_standard_includes(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            directive
            for directive in self.include_directives(macro_table)
            if not directive.get("is_system") and not directive.get("resolved_path")
        ]
