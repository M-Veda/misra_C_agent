"""Phase 4: Linkage Analyzer — ODR-style violation detection and
visibility/storage-duration queries built on top of Phase 3's `LinkageIndex`
(cross-TU symbol occurrences) and `SymbolIndex` (per-TU declarations).

C doesn't have a formal "One Definition Rule" the way C++ does, but MISRA
C:2012 Rule 8.x and plain C linkage semantics impose an equivalent
constraint: every external-linkage identifier must denote exactly one
object/function, with exactly one defining declaration, and every
declaration of it across every translation unit must be *compatible*.
This module names and structures the violations of that constraint that
`LinkageIndex` already had the raw data for, plus a few Phase 3 didn't
check at all (a symbol declared `static` in one TU and non-`static` in
another; a symbol with more than one non-static defining declaration that
supplies an initializer).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from misra_platform_rules.analyzers.linkage_index import LinkageIndex

VISIBILITY_EXTERNAL = "external"
VISIBILITY_INTERNAL = "internal"
VISIBILITY_MIXED = "mixed"
VISIBILITY_UNKNOWN = "unknown"


@dataclass(slots=True)
class OdrViolation:
    name: str
    reason: str
    evidence: list[dict[str, Any]]


class LinkageAnalyzer:
    def __init__(self, linkage_index: LinkageIndex) -> None:
        self.linkage_index = linkage_index

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def visibility(self, name: str) -> str:
        occurrences = self.linkage_index.occurrences(name)
        if not occurrences:
            return VISIBILITY_UNKNOWN
        classes = {o.get("storage_class", "external") for o in occurrences}
        has_static = "static" in classes
        has_non_static = any(c != "static" for c in classes)
        if has_static and has_non_static:
            return VISIBILITY_MIXED
        return VISIBILITY_INTERNAL if has_static else VISIBILITY_EXTERNAL

    def storage_duration(self, name: str) -> str:
        """File-scope declarations (everything `LinkageIndex` tracks) always
        have `static` storage duration in C, regardless of internal/external
        *linkage* — linkage and storage duration are independent axes.
        Automatic-storage-duration locals are per-function and are tracked
        by `DataFlowEngineV2.variable_lifetime_ranges`, not here."""
        return "static" if self.linkage_index.occurrences(name) else "unknown"

    # ------------------------------------------------------------------
    # ODR-style violations
    # ------------------------------------------------------------------

    def linkage_mismatch(self, name: str) -> OdrViolation | None:
        """A symbol declared `static` (internal linkage) in one TU and
        non-`static` (external linkage) in another — undefined behavior in
        C, and always a defect: the two declarations cannot both be
        correct."""
        if self.visibility(name) != VISIBILITY_MIXED:
            return None
        occurrences = self.linkage_index.occurrences(name)
        return OdrViolation(
            name=name,
            reason="linkage_mismatch: declared with internal (static) linkage in one "
            "translation unit and external linkage in another",
            evidence=occurrences,
        )

    def duplicate_definitions(self, name: str) -> OdrViolation | None:
        if not self.linkage_index.has_multiple_definitions(name):
            return None
        return OdrViolation(
            name=name,
            reason="duplicate_definition: more than one translation unit provides an "
            "external-linkage defining declaration (a function body, or an "
            "initialized global) for this identifier",
            evidence=self.linkage_index.definitions(name),
        )

    def incompatible_declarations(self, name: str) -> OdrViolation | None:
        mismatches = self.linkage_index.incompatible_type_spellings(name)
        if not mismatches:
            return None
        return OdrViolation(
            name=name,
            reason=f"incompatible_declaration: conflicting type spellings across "
            f"translation units: {mismatches}",
            evidence=self.linkage_index.external_occurrences(name),
        )

    def odr_violations(self) -> list[OdrViolation]:
        violations: list[OdrViolation] = []
        for name in self.linkage_index.all_names():
            for check in (
                self.linkage_mismatch,
                self.duplicate_definitions,
                self.incompatible_declarations,
            ):
                violation = check(name)
                if violation is not None:
                    violations.append(violation)
        return violations

    def undefined_external_references(self) -> list[str]:
        """External-linkage identifiers referenced/declared somewhere but
        never defined (no occurrence with a body/initializer) anywhere in
        the analyzed project — usually fine (defined in a library not
        analyzed here), reported as informational, not an ODR violation."""
        return [
            name
            for name in self.linkage_index.all_names()
            if self.linkage_index.external_occurrences(name) and not self.linkage_index.definitions(name)
        ]
