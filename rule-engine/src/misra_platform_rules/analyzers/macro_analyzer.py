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

    def preprocessor_directives(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        return macro_table.get("preprocessor_directives", [])

    @staticmethod
    def normalize_header_name(name: str) -> str:
        """Strip delimiters so ``<stdio.h>`` and ``"stdio.h"`` compare equal."""
        stripped = name.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            return stripped[1:-1]
        if stripped.startswith('"') and stripped.endswith('"'):
            return stripped[1:-1]
        return stripped

    def header_matches(self, directive: dict[str, Any], forbidden_headers: set[str]) -> bool:
        header = directive.get("header") or directive.get("included_file", "")
        normalized = self.normalize_header_name(header)
        return normalized in forbidden_headers

    def includes_matching(self, macro_table: dict[str, Any], forbidden_headers: set[str]) -> list[dict[str, Any]]:
        return [d for d in self.include_directives(macro_table) if self.header_matches(d, forbidden_headers)]

    def include_has_invalid_header_chars(self, directive: dict[str, Any]) -> bool:
        if directive.get("invalid_header_chars"):
            return True
        header = directive.get("header") or directive.get("included_file", "")
        return any(marker in header for marker in ('"', "\\", "/*", "//"))

    def include_has_invalid_syntax(self, directive: dict[str, Any]) -> bool:
        return bool(directive.get("invalid_syntax"))

    def include_preceded_by_non_preprocessor(self, directive: dict[str, Any]) -> bool:
        return bool(directive.get("preceded_by_non_preprocessor"))

    def macro_has_invalid_preprocessor_tokens(self, macro_def: dict[str, Any]) -> bool:
        return bool(macro_def.get("invalid_preprocessor_tokens"))

    def macro_stringify_param_unparenthesized_operator(self, macro_def: dict[str, Any]) -> bool:
        return bool(macro_def.get("stringify_param_unparenthesized_operator"))

    def macro_param_mixed_stringify_and_paste(self, macro_def: dict[str, Any]) -> bool:
        return bool(macro_def.get("param_mixed_stringify_and_paste"))

    def conditional_non_boolean_controlling_expression(self, branch: dict[str, Any]) -> bool:
        return branch.get("directive") in ("if", "elif") and bool(
            branch.get("non_boolean_controlling_expression")
        )

    def conditional_undefined_identifiers(self, branch: dict[str, Any]) -> list[str]:
        if branch.get("directive") not in ("if", "elif"):
            return []
        return list(branch.get("undefined_identifiers", []))

    def directive_has_invalid_form(self, directive: dict[str, Any]) -> bool:
        return bool(directive.get("invalid_form"))

    def undef_directives(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        """Phase 7: #undef events emitted by clang-worker PreprocessorMetadata."""
        return macro_table.get("undef_directives", [])

    def macros_using_token_operators(self, macro_table: dict[str, Any]) -> list[dict[str, Any]]:
        """Phase 7: macro definitions whose body uses # and/or ## (Rule 20.10)."""
        return [
            macro_def
            for macro_def in self.macro_definitions(macro_table)
            if macro_def.get("uses_stringify") or macro_def.get("uses_token_paste")
        ]
