"""Phase 3 deliverable: the full MISRA C:2012 rule taxonomy / coverage matrix.

This enumerates every Directive and Rule in MISRA C:2012 (first edition,
143 rules + 4 directive groups), classifies each into an implementation
category (A-G, see `taxonomy.py`), assigns it to a rule pack where
applicable, and records whether the platform currently implements
automated detection for it.

Titles below are short paraphrases for classification/reporting purposes,
not verbatim reproductions of the (copyrighted) MISRA C:2012 rule text.

`implemented_rule_id` is populated by `mark_implemented()` by cross
referencing the live `RuleRegistry`, so this file is the single source of
truth for "did we build this" without needing manual bookkeeping to stay in
sync with the registry.
"""

from dataclasses import dataclass, replace

from misra_platform_rules.taxonomy import RuleImplementationCategory as Cat
from misra_platform_rules.taxonomy import RulePack


@dataclass(frozen=True, slots=True)
class CoverageEntry:
    identifier: str  # e.g. "10.3" or "Dir 4.1"
    kind: str  # "directive" | "rule"
    title: str
    category: Cat
    rule_pack: RulePack | None
    misra_class: str  # mandatory | required | advisory
    unsupported_reason: str | None = None
    implemented_rule_id: str | None = None


def _rule_id(number: str) -> str:
    return f"misra-c2012-rule-{number.replace('.', '-')}"


# fmt: off
_RAW: list[tuple[str, str, str, Cat, RulePack | None, str, str | None]] = [
    # --- Directives -----------------------------------------------------
    ("Dir 1.1", "directive", "Implementation shall be documented/understood", Cat.G_CONFIGURATION_BUILD, None, "required", "Process/toolchain documentation, not code-analyzable"),
    ("Dir 2.1", "directive", "All source files conform to a documented language subset", Cat.G_CONFIGURATION_BUILD, None, "required", "Toolchain configuration, not code-analyzable"),
    ("Dir 3.1", "directive", "All code shall be traceable to requirements", Cat.G_CONFIGURATION_BUILD, None, "required", "Requirements traceability is a process concern"),
    ("Dir 4.1", "directive", "Run-time failures shall be minimized", Cat.G_CONFIGURATION_BUILD, None, "required", "Design-level directive, not mechanically checkable"),
    ("Dir 4.2", "directive", "All documentation shall be comprehensible", Cat.G_CONFIGURATION_BUILD, None, "advisory", "Process concern"),
    ("Dir 4.3", "directive", "Assembly language shall be encapsulated/documented", Cat.G_CONFIGURATION_BUILD, None, "required", "Requires inline-asm block tracking not yet modeled"),
    ("Dir 4.4", "directive", "Sections of code should not be commented out", Cat.G_CONFIGURATION_BUILD, None, "advisory", "Requires raw token/comment stream, not in AST"),
    ("Dir 4.5", "directive", "Identifiers reused across name spaces should be unambiguous", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "advisory", "Planned: extend SymbolIndex with namespace tagging"),
    ("Dir 4.6", "directive", "Typedefs indicating size/signedness should be used over basic types", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "advisory", "Planned"),
    ("Dir 4.7", "directive", "Error information from a function shall be tested", Cat.D_DATA_FLOW, None, "required", "Requires interprocedural return-value dataflow"),
    ("Dir 4.8", "directive", "Object implementation should be hidden if not needed", Cat.G_CONFIGURATION_BUILD, None, "advisory", "Design-level directive"),
    ("Dir 4.9", "directive", "Function-like macros should be avoided", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", "Planned: reuse MacroAnalyzer.function_like_macros"),
    ("Dir 4.10", "directive", "Precautions shall be taken against header re-inclusion", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", "Planned: needs include-guard pattern detection"),
    ("Dir 4.11", "directive", "Validity of values passed to library functions shall be checked", Cat.D_DATA_FLOW, None, "required", "Requires interprocedural value-range analysis"),
    ("Dir 4.12", "directive", "Dynamic memory allocation shall not be used", Cat.A_AST_ONLY, None, "required", "Planned: CallExpr name-match on malloc/calloc/realloc/free"),
    ("Dir 4.13", "directive", "Functions should be called with correct argument count/type", Cat.B_TYPE_SYSTEM, None, "advisory", "Planned"),
    ("Dir 4.14", "directive", "Validity of external inputs shall be checked", Cat.D_DATA_FLOW, None, "required", "Requires taint/provenance tracking"),

    # --- Rule 1: Standard C environment ---------------------------------
    ("1.1", "rule", "Program shall contain no violations of the standard, no undefined/unspecified behaviour relied upon", Cat.G_CONFIGURATION_BUILD, None, "required", "Compiler-diagnostics-level; out of AST-rule scope"),
    ("1.2", "rule", "Language extensions should not be used", Cat.G_CONFIGURATION_BUILD, None, "advisory", "Requires toolchain-profile extension list"),
    ("1.3", "rule", "No occurrence of undefined or critical unspecified behaviour", Cat.D_DATA_FLOW, RulePack.EXPRESSIONS, "required", None),
    ("1.4", "rule", "Emergent language features shall not be used", Cat.G_CONFIGURATION_BUILD, None, "required", "Requires language-standard-version configuration"),

    # --- Rule 2: Unused code ---------------------------------------------
    ("2.1", "rule", "A project shall not contain unreachable code", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("2.2", "rule", "There shall be no dead code", Cat.D_DATA_FLOW, RulePack.INITIALIZATION, "required", None),
    ("2.3", "rule", "A project should not contain unused type declarations", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "advisory", None),
    ("2.4", "rule", "A project should not contain unused tag declarations", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "advisory", None),
    ("2.5", "rule", "A project should not contain unused macro declarations", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("2.6", "rule", "A function should not contain unused label declarations", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "advisory", None),
    ("2.7", "rule", "A function should not contain unused parameters", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "advisory", None),

    # --- Rule 3: Comments ------------------------------------------------
    ("3.1", "rule", "Character sequences /* and // shall not be used in a comment", Cat.G_CONFIGURATION_BUILD, None, "required", "Requires raw token/comment stream, not in AST"),
    ("3.2", "rule", "Line-splicing shall not be used in a comment", Cat.G_CONFIGURATION_BUILD, None, "required", "Requires raw token/comment stream"),

    # --- Rule 4: Lexical conventions -------------------------------------
    ("4.1", "rule", "Octal and hexadecimal escape sequences shall be terminated", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("4.2", "rule", "Trigraphs should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", "Requires raw source text scan"),

    # --- Rule 5: Identifiers ----------------------------------------------
    ("5.1", "rule", "External identifiers shall be distinct", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "required", None),
    ("5.2", "rule", "Identifiers declared in the same scope/name space shall be distinct", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("5.3", "rule", "An identifier declared in an inner scope shall not hide one in an outer scope", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("5.4", "rule", "Macro identifiers shall be distinct", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("5.5", "rule", "Identifiers shall be distinct from macro names", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("5.6", "rule", "A typedef name shall be a unique identifier", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("5.7", "rule", "A tag name shall be a unique identifier", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("5.8", "rule", "Identifiers with external linkage shall be distinct", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "required", None),
    ("5.9", "rule", "Identifiers with internal linkage should be distinct", Cat.A_AST_ONLY, RulePack.LINKAGE, "advisory", None),

    # --- Rule 6: Types ------------------------------------------------------
    ("6.1", "rule", "Bit-field types shall only be declared as explicit unsigned/signed int", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "required", None),
    ("6.2", "rule", "Single-bit named bit-fields shall not be of a signed type", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "required", None),

    # --- Rule 7: Literals and constants -------------------------------------
    ("7.1", "rule", "Octal constants (other than zero) shall not be used", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("7.2", "rule", "A 'u' or 'U' suffix shall be applied to unsigned integer constants", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("7.3", "rule", "The lowercase 'l' suffix shall not be used", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("7.4", "rule", "A string literal shall not be assigned to an object unless it is const-qualified", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "required", None),

    # --- Rule 8: Declarations and definitions --------------------------------
    ("8.1", "rule", "Types shall be explicitly specified", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("8.2", "rule", "Function types shall be in prototype form with named parameters", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("8.3", "rule", "All declarations of an object/function shall use the same names and qualifiers", Cat.B_TYPE_SYSTEM, RulePack.DECLARATIONS, "required", None),
    ("8.4", "rule", "A compatible declaration shall be visible for externally-linked objects/functions", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "required", None),
    ("8.5", "rule", "An external object/function shall be declared once in one file", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "required", None),
    ("8.6", "rule", "An identifier with external linkage shall have exactly one definition", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.DECLARATIONS, "required", None),
    ("8.7", "rule", "Functions/objects used in only one translation unit should have internal linkage", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "advisory", None),
    ("8.8", "rule", "The static storage class specifier shall be used consistently", Cat.A_AST_ONLY, RulePack.LINKAGE, "required", None),
    ("8.9", "rule", "An object should be defined at block scope if its identifier is used in one function only", Cat.D_DATA_FLOW, RulePack.STORAGE_DURATION, "advisory", None),
    ("8.10", "rule", "An inline function shall be declared with internal linkage", Cat.A_AST_ONLY, RulePack.LINKAGE, "required", None),
    ("8.11", "rule", "An array with external linkage should be declared with an explicit size", Cat.B_TYPE_SYSTEM, RulePack.DECLARATIONS, "advisory", None),
    ("8.12", "rule", "Within an enumerator list the value of an implicit enumerator shall be unique", Cat.B_TYPE_SYSTEM, RulePack.DECLARATIONS, "required", None),
    ("8.13", "rule", "A pointer should point to a const-qualified type where possible", Cat.D_DATA_FLOW, RulePack.DECLARATIONS, "advisory", None),
    ("8.14", "rule", "The restrict qualifier shall not be used", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),

    # --- Rule 9: Initialization -----------------------------------------------
    ("9.1", "rule", "Automatic objects shall be initialized before use", Cat.D_DATA_FLOW, RulePack.INITIALIZATION, "mandatory", None),
    ("9.2", "rule", "Initializers for aggregates/unions shall be fully bracketed", Cat.A_AST_ONLY, RulePack.INITIALIZATION, "required", None),
    ("9.3", "rule", "Array elements shall not be initialized more than once (arrays)", Cat.A_AST_ONLY, RulePack.INITIALIZATION, "required", None),
    ("9.4", "rule", "An element of an object shall not be initialized more than once", Cat.A_AST_ONLY, RulePack.INITIALIZATION, "required", None),
    ("9.5", "rule", "Designated initializers should not be mixed with non-designated for the same array", Cat.A_AST_ONLY, RulePack.INITIALIZATION, "advisory", None),

    # --- Rule 10: The essential type model --------------------------------------
    ("10.1", "rule", "Operands shall not be of an inappropriate essential type", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "required", None),
    ("10.2", "rule", "Character/string operands' essential types shall be appropriate", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "required", None),
    ("10.3", "rule", "Value shall not be assigned to a narrower/different-category essential type", Cat.B_TYPE_SYSTEM, RulePack.ESSENTIAL_TYPES, "required", None),
    ("10.4", "rule", "Operands of an operator shall have the same essential type category", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "required", None),
    ("10.5", "rule", "A cast should not change an essential type category", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "advisory", None),
    ("10.6", "rule", "The value of a composite expression shall not be assigned to a wider essential type", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "required", None),
    ("10.7", "rule", "A composite expression's essential type shall not be cast to an incompatible category before use as an operand", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "required", None),
    ("10.8", "rule", "A composite expression cast to a wider/different category shall not be used as an operand", Cat.B_TYPE_SYSTEM, RulePack.CONVERSIONS, "required", None),

    # --- Rule 11: Pointer type conversions ----------------------------------------
    ("11.1", "rule", "Conversions shall not be performed between a pointer to function and any other type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.2", "rule", "Conversions shall not be performed between a pointer to an incomplete type and any other type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.3", "rule", "A cast shall not convert a pointer to an object type to a pointer to a different object type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.4", "rule", "A conversion should not be performed between a pointer and an integer type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "advisory", None),
    ("11.5", "rule", "A conversion from pointer-to-void into pointer-to-object should not be performed", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "advisory", None),
    ("11.6", "rule", "A cast shall not convert a pointer to void into an arithmetic type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.7", "rule", "A cast shall not convert a pointer type to a non-integer arithmetic type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.8", "rule", "A cast shall not remove const/volatile qualification from a pointer target", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("11.9", "rule", "NULL shall be the only integer null-pointer-constant used", Cat.A_AST_ONLY, RulePack.POINTERS, "required", None),

    # --- Rule 12: Expressions ---------------------------------------------------
    ("12.1", "rule", "The precedence of operators within expressions should be made explicit", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "advisory", None),
    ("12.2", "rule", "The right-hand operand of a shift shall lie in [0, width-1]", Cat.B_TYPE_SYSTEM, RulePack.EXPRESSIONS, "required", None),
    ("12.3", "rule", "The comma operator should not be used", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "advisory", None),
    ("12.4", "rule", "Evaluation of constant unsigned integer expressions should not wrap", Cat.B_TYPE_SYSTEM, RulePack.EXPRESSIONS, "advisory", None),
    ("12.5", "rule", "sizeof on an array function parameter shall not be taken", Cat.B_TYPE_SYSTEM, RulePack.EXPRESSIONS, "mandatory", None),

    # --- Rule 13: Side effects ------------------------------------------------
    ("13.1", "rule", "Initializer lists shall not contain persistent side effects", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("13.2", "rule", "The value of an expression shall be the same under any permitted evaluation order", Cat.D_DATA_FLOW, RulePack.EXPRESSIONS, "required", None),
    ("13.3", "rule", "A full expression containing an increment/decrement should have no other potential side effect", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "advisory", None),
    ("13.4", "rule", "The result of an assignment operator should not be used", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "advisory", None),
    ("13.5", "rule", "The right-hand operand of && or || shall not contain persistent side effects", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("13.6", "rule", "The operand of sizeof shall not contain a persistent side effect", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "mandatory", None),

    # --- Rule 14: Control statement expressions ----------------------------------
    ("14.1", "rule", "A loop counter shall not have essentially floating type", Cat.B_TYPE_SYSTEM, RulePack.CONTROL_FLOW, "required", None),
    ("14.2", "rule", "A for loop shall be well-formed (init/condition/counter)", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("14.3", "rule", "Controlling expressions shall not be invariant", Cat.D_DATA_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("14.4", "rule", "The controlling expression of an if/iteration statement shall have essentially Boolean type", Cat.B_TYPE_SYSTEM, RulePack.EXPRESSIONS, "required", None),

    # --- Rule 15: Control flow -------------------------------------------------
    ("15.1", "rule", "The goto statement should not be used", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "advisory", None),
    ("15.2", "rule", "A goto statement shall jump to a label in the same or an enclosing block", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("15.3", "rule", "Any label referenced by goto shall be declared in the same/enclosing block", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("15.4", "rule", "There should be no more than one break/goto used to terminate a loop", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "advisory", None),
    ("15.5", "rule", "A function should have a single point of exit at the end", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "advisory", None),
    ("15.6", "rule", "Bodies of iteration/selection statements shall be a compound statement", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),
    ("15.7", "rule", "An if-else-if construct shall be terminated with an else clause", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),

    # --- Rule 16: Switch statements ---------------------------------------------
    ("16.1", "rule", "All switch statements shall be well-formed", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("16.2", "rule", "A switch label shall only be used within a switch statement's compound statement", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),
    ("16.3", "rule", "An unconditional break shall terminate every switch clause", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "required", None),
    ("16.4", "rule", "Every switch statement shall have a default label", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),
    ("16.5", "rule", "A default label shall appear as either the first or last switch label", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),
    ("16.6", "rule", "Every switch statement shall have at least two switch clauses", Cat.A_AST_ONLY, RulePack.CONTROL_FLOW, "required", None),
    ("16.7", "rule", "A switch-expression shall not have essentially Boolean type", Cat.B_TYPE_SYSTEM, RulePack.CONTROL_FLOW, "required", None),

    # --- Rule 17: Functions --------------------------------------------------
    ("17.1", "rule", "The features of <stdarg.h> shall not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("17.2", "rule", "Functions shall not call themselves, directly or indirectly (no recursion)", Cat.E_CROSS_TRANSLATION_UNIT, RulePack.LINKAGE, "required", None),
    ("17.3", "rule", "A function shall not be declared implicitly", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "mandatory", None),
    ("17.4", "rule", "All exit paths from a non-void function shall have an explicit return with a value", Cat.C_CONTROL_FLOW, RulePack.CONTROL_FLOW, "mandatory", None),
    ("17.5", "rule", "Array function arguments should match the array declared for the parameter", Cat.B_TYPE_SYSTEM, RulePack.DECLARATIONS, "advisory", None),
    ("17.6", "rule", "The declaration of an array parameter shall not contain the static keyword", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "mandatory", None),
    ("17.7", "rule", "The value returned by a non-void function shall be used or explicitly cast to void", Cat.A_AST_ONLY, RulePack.EXPRESSIONS, "required", None),
    ("17.8", "rule", "A function parameter should not be modified", Cat.D_DATA_FLOW, RulePack.DECLARATIONS, "advisory", None),

    # --- Rule 18: Pointers and arrays -----------------------------------------
    ("18.1", "rule", "Pointer arithmetic shall only address within an array's bounds", Cat.D_DATA_FLOW, RulePack.POINTERS, "required", None),
    ("18.2", "rule", "Subtraction between pointers shall only be applied to elements of the same array", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("18.3", "rule", "Relational operators shall only be applied to pointers into the same object", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "required", None),
    ("18.4", "rule", "+, -, += and -= should not be applied to an expression of pointer type", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "advisory", None),
    ("18.5", "rule", "Declarations should contain no more than two levels of pointer nesting", Cat.B_TYPE_SYSTEM, RulePack.POINTERS, "advisory", None),
    ("18.6", "rule", "The address of an automatic object shall not escape its lifetime", Cat.D_DATA_FLOW, RulePack.STORAGE_DURATION, "required", None),
    ("18.7", "rule", "Flexible array members shall not be declared", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "required", None),
    ("18.8", "rule", "Variable-length array types shall not be used", Cat.B_TYPE_SYSTEM, RulePack.DECLARATIONS, "required", None),

    # --- Rule 19: Overlapping storage -----------------------------------------
    ("19.1", "rule", "An object shall not be assigned/copied to an overlapping object", Cat.D_DATA_FLOW, RulePack.POINTERS, "mandatory", None),
    ("19.2", "rule", "The union keyword should not be used", Cat.A_AST_ONLY, RulePack.DECLARATIONS, "advisory", None),

    # --- Rule 20: Preprocessing directives -------------------------------------
    ("20.1", "rule", "#include directives should only be preceded by preprocessor directives/comments", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("20.2", "rule", "The ' \" or \\ characters and /* or // sequences shall not occur in a header name", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.3", "rule", "#include directives shall use the correct syntax", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.4", "rule", "A macro shall not be defined with the same name as a language keyword", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.5", "rule", "#undef should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("20.6", "rule", "Tokens introduced by # or ## shall be valid preprocessing tokens", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.7", "rule", "Expressions from macro parameters shall be enclosed in parentheses", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.8", "rule", "The controlling expression of a #if/#elif shall evaluate to 0 or 1", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.9", "rule", "All identifiers in a #if/#elif preprocessing expression shall be defined", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.10", "rule", "The # and ## preprocessor operators should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("20.11", "rule", "A macro parameter with # shall not be followed by a non-parenthesized operator", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.12", "rule", "A macro parameter used with # and without # shall not also be used with ##", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.13", "rule", "A line with a # directive shall have one of the permitted forms", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("20.14", "rule", "#if/#ifdef/#ifndef and matching #endif shall be in the same file", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),

    # --- Rule 21: Standard libraries ---------------------------------------------
    ("21.1", "rule", "#define/#undef shall not be used on reserved identifiers/keywords", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("21.2", "rule", "A reserved identifier or macro name shall not be declared", Cat.A_AST_ONLY, RulePack.PREPROCESSOR, "required", None),
    ("21.3", "rule", "The memory allocation/deallocation functions of <stdlib.h> shall not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.4", "rule", "The features of <setjmp.h> shall not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("21.5", "rule", "The features of <signal.h> shall not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("21.6", "rule", "The Standard Library input/output functions should not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.7", "rule", "The atof/atoi/atol/atoll functions shall not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.8", "rule", "The library functions abort/exit/getenv/system shall not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.9", "rule", "The library functions bsearch and qsort should not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "advisory", None),
    ("21.10", "rule", "The features of <time.h> should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "required", None),
    ("21.11", "rule", "The features of <tgmath.h> should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("21.12", "rule", "The exception-handling features of <fenv.h> should not be used", Cat.F_PREPROCESSOR, RulePack.PREPROCESSOR, "advisory", None),
    ("21.13", "rule", "Any value passed to a <ctype.h> function shall be representable as unsigned char or EOF", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("21.14", "rule", "memcmp shall not be used to compare null-terminated strings", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.15", "rule", "Pointer arguments to memcpy/memmove/memcmp shall be pointers to compatible types", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "required", None),
    ("21.16", "rule", "Pointer arguments to memcmp should point to a pointer, essentially signed/unsigned char, or void type", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "advisory", None),
    ("21.17", "rule", "String handling functions shall not cause overflow/underflow of the string buffer", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("21.18", "rule", "The size_t argument passed to a string/memory function shall not exceed the destination object size", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("21.19", "rule", "Pointers returned by locale/string library functions shall only be used as if pointing to const-qualified type", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("21.20", "rule", "A pointer to a string returned by certain library functions shall not be used after a subsequent call", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("21.21", "rule", "The system function of <stdlib.h> shall not be used", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),

    # --- Rule 22: Resource management ---------------------------------------------
    ("22.1", "rule", "All resources obtained dynamically shall be explicitly released", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "required", None),
    ("22.2", "rule", "A resource obtained shall not be released more than once", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("22.3", "rule", "The same file/stream should not be open for read and write at the same time in different streams", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "advisory", None),
    ("22.4", "rule", "There shall be no attempt to write to a stream opened as read-only", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("22.5", "rule", "A pointer to a FILE object shall not be dereferenced", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("22.6", "rule", "The value of a pointer to a FILE object shall not be used after the stream is closed", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "mandatory", None),
    ("22.7", "rule", "The macro EOF shall only be compared with the unmodified return value of a stream input function", Cat.B_TYPE_SYSTEM, RulePack.STANDARD_LIBRARY, "required", None),
    ("22.8", "rule", "The value of errno shall be set to zero before calling an errno-setting function", Cat.A_AST_ONLY, RulePack.STANDARD_LIBRARY, "required", None),
    ("22.9", "rule", "The value of errno shall be tested against zero after calling an errno-setting function", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "required", None),
    ("22.10", "rule", "The value of errno shall only be tested when the function return value indicates failure", Cat.D_DATA_FLOW, RulePack.STANDARD_LIBRARY, "required", None),
]
# fmt: on


def build_coverage_matrix() -> list[CoverageEntry]:
    entries: list[CoverageEntry] = []
    for identifier, kind, title, category, pack, misra_class, unsupported_reason in _RAW:
        implemented_rule_id = None
        if unsupported_reason is None and kind == "rule":
            implemented_rule_id = _rule_id(identifier)
        entries.append(
            CoverageEntry(
                identifier=identifier,
                kind=kind,
                title=title,
                category=category,
                rule_pack=pack,
                misra_class=misra_class,
                unsupported_reason=unsupported_reason,
                implemented_rule_id=implemented_rule_id,
            )
        )
    return entries


def mark_implemented(entries: list[CoverageEntry], registered_rule_ids: set[str]) -> list[CoverageEntry]:
    """Cross-reference against a live `RuleRegistry.list_rule_ids()` so
    "implemented" always reflects what's actually registered, not just what
    this file claims should be implementable."""
    updated: list[CoverageEntry] = []
    for entry in entries:
        if entry.implemented_rule_id and entry.implemented_rule_id not in registered_rule_ids:
            updated.append(
                replace(
                    entry,
                    implemented_rule_id=None,
                    unsupported_reason=entry.unsupported_reason or "Not yet registered",
                )
            )
        else:
            updated.append(entry)
    return updated


def summary(entries: list[CoverageEntry]) -> dict[str, int]:
    total_rules = sum(1 for e in entries if e.kind == "rule")
    implemented = sum(1 for e in entries if e.implemented_rule_id)
    by_category: dict[str, int] = {}
    for entry in entries:
        by_category[entry.category.value] = by_category.get(entry.category.value, 0) + 1
    return {
        "total_directives": sum(1 for e in entries if e.kind == "directive"),
        "total_rules": total_rules,
        "implemented_rules": implemented,
        "unsupported_rules": total_rules - implemented,
        **{f"category_{key}": value for key, value in by_category.items()},
    }
