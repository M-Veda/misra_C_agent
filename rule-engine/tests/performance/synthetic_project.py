"""Synthetic C-project generator used to benchmark the rule engine.

We don't have a real 100K/500K LOC embedded C codebase (or a running
clang-worker) available in this environment, so performance is measured
against synthetic ASTs that are structurally representative of typical
embedded C: functions with local declarations, arithmetic, casts,
conditionals, switches, pointer use, and calls. Throughput is measured at a
modest scale and then extrapolated linearly to the 100K/500K LOC targets.

Each synthetic function is built to be ~15 source lines and ~18 AST nodes,
which is a reasonable approximation for average embedded-C function size.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TESTS_DIR = Path(__file__).resolve().parent.parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from conformance.ast_builders import Builder  # noqa: E402

LINES_PER_FUNCTION = 15
FUNCTIONS_PER_TU = 40
LOC_PER_TU = LINES_PER_FUNCTION * FUNCTIONS_PER_TU


def _add_function(builder: Builder, index: int, tu_index: int) -> None:
    fn = builder.node(
        "FunctionDecl",
        semantic_properties={"name": f"tu{tu_index}_func_{index}", "storage_class": "static"},
    )
    body = builder.node("CompoundStmt", parent=fn)

    decl = builder.node(
        "VarDecl",
        parent=body,
        essential_type="signed_int",
        semantic_properties={"name": f"local_{index}", "has_initializer": True},
    )
    builder.node("IntegerLiteral", parent=decl, essential_type="signed_int")

    assign = builder.node("BinaryOperator", parent=body, semantic_properties={"opcode": "+="})
    builder.node("DeclRefExpr", parent=assign, essential_type="signed_int")
    literal = builder.node("IntegerLiteral", parent=assign, essential_type="signed_int")

    cast = builder.node("CStyleCastExpr", parent=body, essential_type="unsigned_char")
    builder.node("DeclRefExpr", parent=cast, essential_type="signed_int")

    if_stmt = builder.node("IfStmt", parent=body)
    condition = builder.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "!="})
    builder.node("DeclRefExpr", parent=condition, essential_type="signed_int")
    builder.node("IntegerLiteral", parent=condition, essential_type="signed_int")
    then_branch = builder.node("CompoundStmt", parent=if_stmt)
    call = builder.node("CallExpr", parent=then_branch, semantic_properties={"callee": "do_work"})
    builder.node("DeclRefExpr", parent=call, essential_type="signed_int")

    if index % 5 == 0:
        switch_stmt = builder.node("SwitchStmt", parent=body)
        for case_value in range(2):
            case_node = builder.node("CaseStmt", parent=switch_stmt)
            builder.node("ReturnStmt", parent=case_node)
        default_node = builder.node("DefaultStmt", parent=switch_stmt)
        builder.node("BreakStmt", parent=default_node)

    ret = builder.node("ReturnStmt", parent=body)
    builder.node("DeclRefExpr", parent=ret, essential_type="signed_int")
    _ = literal


def build_translation_unit(tu_index: int, functions_per_tu: int = FUNCTIONS_PER_TU) -> dict[str, Any]:
    builder = Builder()
    for index in range(functions_per_tu):
        _add_function(builder, index, tu_index)
    return builder.artifact(file_path=f"synthetic/tu_{tu_index}.c")


@dataclass(slots=True)
class SyntheticProject:
    artifacts: list[dict[str, Any]]
    loc_total: int
    functions_total: int
    translation_units: int


def build_project(*, translation_units: int, functions_per_tu: int = FUNCTIONS_PER_TU) -> SyntheticProject:
    artifacts = [
        build_translation_unit(tu_index, functions_per_tu=functions_per_tu)
        for tu_index in range(translation_units)
    ]
    return SyntheticProject(
        artifacts=artifacts,
        loc_total=translation_units * functions_per_tu * LINES_PER_FUNCTION,
        functions_total=translation_units * functions_per_tu,
        translation_units=translation_units,
    )
