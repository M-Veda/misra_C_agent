"""Phase 3 rule taxonomy: implementation categories, rule packs, and execution groups.

Every rule is classified along two independent axes:

1. Implementation category (A-G) — *how* the rule must be detected, i.e. which
   analysis capability it fundamentally requires. This determines execution
   ordering: cheap, purely-structural categories run before expensive
   whole-program categories.
2. Rule pack — a *thematic* grouping used for product organization, coverage
   reporting, and shared-infrastructure reuse (e.g. every rule in the
   "Essential Types" pack reuses `EssentialTypeAnalyzer`).
"""

from enum import StrEnum


class RuleImplementationCategory(StrEnum):
    """Category A-G from the Phase 3 rule taxonomy."""

    A_AST_ONLY = "A_ast_only"
    B_TYPE_SYSTEM = "B_type_system"
    C_CONTROL_FLOW = "C_control_flow"
    D_DATA_FLOW = "D_data_flow"
    E_CROSS_TRANSLATION_UNIT = "E_cross_translation_unit"
    F_PREPROCESSOR = "F_preprocessor"
    G_CONFIGURATION_BUILD = "G_configuration_build"


# Execution order: cheapest / most-local categories first. A rule dispatcher
# can use this to run category A/B/F rules (single-TU, no whole-program state)
# fully in parallel, then C/D (need a CFG/dataflow pass built once per
# function), then E/G last (need project-wide or build-system state).
CATEGORY_EXECUTION_ORDER: dict[RuleImplementationCategory, int] = {
    RuleImplementationCategory.A_AST_ONLY: 0,
    RuleImplementationCategory.F_PREPROCESSOR: 0,
    RuleImplementationCategory.B_TYPE_SYSTEM: 1,
    RuleImplementationCategory.C_CONTROL_FLOW: 2,
    RuleImplementationCategory.D_DATA_FLOW: 3,
    RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT: 4,
    RuleImplementationCategory.G_CONFIGURATION_BUILD: 4,
}

CATEGORY_DESCRIPTIONS: dict[RuleImplementationCategory, str] = {
    RuleImplementationCategory.A_AST_ONLY: (
        "Detectable from raw AST shape/kind alone (node kinds, literal presence, "
        "structural patterns). No type or control-flow reasoning required."
    ),
    RuleImplementationCategory.B_TYPE_SYSTEM: (
        "Requires essential-type / canonical-type / qualifier information "
        "attached to AST nodes (casts, conversions, narrowing, qualifiers)."
    ),
    RuleImplementationCategory.C_CONTROL_FLOW: (
        "Requires a control-flow view of a function body (exit points, "
        "reachability, switch fallthrough, loop structure)."
    ),
    RuleImplementationCategory.D_DATA_FLOW: (
        "Requires tracking definitions/uses of variables across statements "
        "(uninitialized use, dead stores, value-never-read)."
    ),
    RuleImplementationCategory.E_CROSS_TRANSLATION_UNIT: (
        "Requires information from more than one translation unit (linkage "
        "consistency, duplicate external identifiers, one-definition rule)."
    ),
    RuleImplementationCategory.F_PREPROCESSOR: (
        "Requires macro table / conditional-compilation metadata rather than "
        "the post-preprocessing AST."
    ),
    RuleImplementationCategory.G_CONFIGURATION_BUILD: (
        "Requires build-system or toolchain configuration (compiler options, "
        "language extensions enabled, target ABI) rather than source alone."
    ),
}


class RulePack(StrEnum):
    """Thematic grouping used for product organization and shared infra reuse."""

    ESSENTIAL_TYPES = "essential_types"
    DECLARATIONS = "declarations"
    POINTERS = "pointers"
    CONTROL_FLOW = "control_flow"
    PREPROCESSOR = "preprocessor"
    EXPRESSIONS = "expressions"
    INITIALIZATION = "initialization"
    STORAGE_DURATION = "storage_duration"
    LINKAGE = "linkage"
    CONVERSIONS = "conversions"
    STANDARD_LIBRARY = "standard_library"


RULE_PACK_PRIMARY_ANALYZER: dict[RulePack, str] = {
    RulePack.ESSENTIAL_TYPES: "EssentialTypeAnalyzer",
    RulePack.DECLARATIONS: "SymbolIndex",
    RulePack.POINTERS: "PointerAnalyzer",
    RulePack.CONTROL_FLOW: "CFGBuilder",
    RulePack.PREPROCESSOR: "MacroAnalyzer",
    RulePack.EXPRESSIONS: "ExpressionClassifier",
    RulePack.INITIALIZATION: "DataFlowEngine",
    RulePack.STORAGE_DURATION: "SymbolIndex",
    RulePack.LINKAGE: "LinkageIndex",
    RulePack.CONVERSIONS: "CastAnalyzer",
    RulePack.STANDARD_LIBRARY: "ASTQuery",
}
