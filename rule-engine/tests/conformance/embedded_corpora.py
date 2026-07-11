"""Phase 4 deliverable: conformance/validation corpora modeled on idioms from
four widely-used embedded C codebases (STM32 HAL, CMSIS, FreeRTOS, lwIP).

We don't have a live clang-worker or the real source trees available in this
sandboxed environment (see `tests/performance/synthetic_project.py` for the
same constraint), so each corpus is a small, hand-built synthetic AST that
faithfully reproduces the *shape* of characteristic constructs from that
codebase: memory-mapped-register pointer casts and bit manipulation (HAL/
CMSIS), linked-list/pointer-chain traversal and function-pointer callbacks
(FreeRTOS), and buffer pointer arithmetic/casting (lwIP).

These functions are intentionally written as idiomatic, production-realistic
code (not MISRA test vectors), so the corpus can be used the way the Phase 4
brief asks: run the full rule registry over it and report what breaks
(crashes), what unsupported constructs remain, and what fires (which for
mature embedded code legitimately includes some real, expected MISRA
findings around pointer/register-cast patterns -- those are noted rather
than treated as bugs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from conformance.ast_builders import Builder


@dataclass(slots=True)
class CorpusUnit:
    corpus: str
    function_name: str
    description: str
    known_constructs: list[str]
    artifact: dict[str, Any]


def _stm32_hal_gpio_write_pin() -> CorpusUnit:
    """`HAL_GPIO_WritePin`-style register bit set/clear via a pointer cast
    to a memory-mapped peripheral struct -- the single most common MISRA
    Rule 11.x / 18.4 deviation pattern in real HAL code."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "HAL_GPIO_WritePin", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    # GPIOx->BSRR = (uint32_t)PinState << PinPos;
    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    member = b.node("MemberExpr", parent=assign, semantic_properties={"member": "BSRR"})
    cast = b.node("CStyleCastExpr", parent=member, essential_type="unsigned_int")
    b.node("DeclRefExpr", parent=cast, semantic_properties={"name": "GPIOx"}, essential_type="unknown")
    shift = b.node("BinaryOperator", parent=assign, semantic_properties={"opcode": "<<"})
    cast2 = b.node("CStyleCastExpr", parent=shift, essential_type="unsigned_int")
    b.node("DeclRefExpr", parent=cast2, semantic_properties={"name": "PinState"}, essential_type="signed_int")
    b.node("DeclRefExpr", parent=shift, semantic_properties={"name": "PinPos"}, essential_type="unsigned_int")

    b.node("ReturnStmt", parent=body)

    return CorpusUnit(
        corpus="stm32_hal",
        function_name="HAL_GPIO_WritePin",
        description="Register bit-set via pointer-to-struct cast (classic HAL peripheral access).",
        known_constructs=["CStyleCastExpr-to-pointer", "MemberExpr", "bit-shift assignment"],
        artifact=b.artifact(file_path="stm32_hal/gpio.c"),
    )


def _stm32_hal_uart_transmit() -> CorpusUnit:
    """`HAL_UART_Transmit`-style status-checked API: NULL guard with early
    return, a bounded for-loop, and an enum-like status return -- exercises
    CFG branching + Rule 17.4 (all exits return a value) + Rule 14.4
    (essentially-Boolean controlling expressions)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "HAL_UART_Transmit", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    if_stmt = b.node("IfStmt", parent=body)
    cond = b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "=="})
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "huart"}, essential_type="unknown")
    b.node("IntegerLiteral", parent=cond, essential_type="signed_int", semantic_properties={"value": "0"})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    ret_err = b.node("ReturnStmt", parent=then_branch)
    b.node("DeclRefExpr", parent=ret_err, semantic_properties={"name": "HAL_ERROR"}, essential_type="unknown")

    for_stmt = b.node("ForStmt", parent=body)
    decl = b.node("VarDecl", parent=for_stmt, essential_type="unsigned_short", semantic_properties={"name": "i", "has_initializer": True})
    b.node("IntegerLiteral", parent=decl, essential_type="unsigned_short")
    loop_cond = b.node("BinaryOperator", parent=for_stmt, semantic_properties={"opcode": "<"})
    b.node("DeclRefExpr", parent=loop_cond, semantic_properties={"name": "i"}, essential_type="unsigned_short")
    b.node("DeclRefExpr", parent=loop_cond, semantic_properties={"name": "Size"}, essential_type="unsigned_short")
    incr = b.node("UnaryOperator", parent=for_stmt, semantic_properties={"opcode": "++"})
    b.node("DeclRefExpr", parent=incr, semantic_properties={"name": "i"}, essential_type="unsigned_short")
    for_body = b.node("CompoundStmt", parent=for_stmt)
    store = b.node("BinaryOperator", parent=for_body, semantic_properties={"opcode": "="})
    member = b.node("MemberExpr", parent=store, semantic_properties={"member": "DR"})
    b.node("DeclRefExpr", parent=member, semantic_properties={"name": "huart"}, essential_type="unknown")
    subscript = b.node("ArraySubscriptExpr", parent=store)
    b.node("DeclRefExpr", parent=subscript, semantic_properties={"name": "pData"}, essential_type="unknown")
    b.node("DeclRefExpr", parent=subscript, semantic_properties={"name": "i"}, essential_type="unsigned_short")

    ret_ok = b.node("ReturnStmt", parent=body)
    b.node("DeclRefExpr", parent=ret_ok, semantic_properties={"name": "HAL_OK"}, essential_type="unknown")

    return CorpusUnit(
        corpus="stm32_hal",
        function_name="HAL_UART_Transmit",
        description="NULL-guard early-return + bounded transmit loop + status enum return.",
        known_constructs=["IfStmt early-return", "ForStmt", "ArraySubscriptExpr", "MemberExpr store"],
        artifact=b.artifact(file_path="stm32_hal/uart.c"),
    )


def _cmsis_nvic_enable_irq() -> CorpusUnit:
    """`NVIC_EnableIRQ`-style bit manipulation into a memory-mapped register
    array, with the shift/mask arithmetic a function-like macro would
    normally expand to (`NVIC->ISER[irq >> 5] |= (1UL << (irq & 0x1F))`)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "NVIC_EnableIRQ", "storage_class": "static", "is_inline": True},
    )
    body = b.node("CompoundStmt", parent=fn)

    assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "|="})
    subscript = b.node("ArraySubscriptExpr", parent=assign)
    member = b.node("MemberExpr", parent=subscript, semantic_properties={"member": "ISER"})
    b.node("DeclRefExpr", parent=member, semantic_properties={"name": "NVIC"}, essential_type="unknown")
    index_shift = b.node("BinaryOperator", parent=subscript, semantic_properties={"opcode": ">>"})
    cast = b.node("CStyleCastExpr", parent=index_shift, essential_type="unsigned_int")
    b.node("DeclRefExpr", parent=cast, semantic_properties={"name": "IRQn"}, essential_type="signed_int")
    b.node("IntegerLiteral", parent=index_shift, essential_type="signed_int", semantic_properties={"value": "5"})

    rhs_shift = b.node("BinaryOperator", parent=assign, semantic_properties={"opcode": "<<"})
    b.node("IntegerLiteral", parent=rhs_shift, essential_type="unsigned_long", semantic_properties={"value": "1"})
    mask = b.node("BinaryOperator", parent=rhs_shift, semantic_properties={"opcode": "&"})
    cast2 = b.node("CStyleCastExpr", parent=mask, essential_type="unsigned_int")
    b.node("DeclRefExpr", parent=cast2, semantic_properties={"name": "IRQn"}, essential_type="signed_int")
    b.node("IntegerLiteral", parent=mask, essential_type="unsigned_int", semantic_properties={"value": "0x1F"})

    return CorpusUnit(
        corpus="cmsis",
        function_name="NVIC_EnableIRQ",
        description="Shift/mask register-array bit manipulation (typical expanded CMSIS macro body).",
        known_constructs=["ArraySubscriptExpr on MemberExpr", "nested shift/mask BinaryOperator"],
        artifact=b.artifact(file_path="cmsis/core_cm.c"),
    )


def _cmsis_systick_config() -> CorpusUnit:
    """`SysTick_Config`-style configuration function: several sequential
    register-field writes then a range-check-guarded return -- exercises
    Rule 10.x essential-type conversions across field assignments."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "SysTick_Config", "storage_class": "static", "is_inline": True},
        essential_type="unsigned_int",
    )
    body = b.node("CompoundStmt", parent=fn)

    if_stmt = b.node("IfStmt", parent=body)
    cond = b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": ">"})
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "ticks"}, essential_type="unsigned_long")
    b.node("IntegerLiteral", parent=cond, essential_type="unsigned_long", semantic_properties={"value": "0xFFFFFF"})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    ret_fail = b.node("ReturnStmt", parent=then_branch)
    b.node("IntegerLiteral", parent=ret_fail, essential_type="unsigned_int", semantic_properties={"value": "1"})

    load_assign = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    load_member = b.node("MemberExpr", parent=load_assign, semantic_properties={"member": "LOAD"})
    b.node("DeclRefExpr", parent=load_member, semantic_properties={"name": "SysTick"}, essential_type="unknown")
    sub = b.node("BinaryOperator", parent=load_assign, semantic_properties={"opcode": "-"})
    b.node("DeclRefExpr", parent=sub, semantic_properties={"name": "ticks"}, essential_type="unsigned_long")
    b.node("IntegerLiteral", parent=sub, essential_type="signed_int", semantic_properties={"value": "1"})

    ret_ok = b.node("ReturnStmt", parent=body)
    b.node("IntegerLiteral", parent=ret_ok, essential_type="unsigned_int", semantic_properties={"value": "0"})

    return CorpusUnit(
        corpus="cmsis",
        function_name="SysTick_Config",
        description="Range-guarded early return followed by register-field configuration writes.",
        known_constructs=["IfStmt range guard", "MemberExpr store with arithmetic RHS"],
        artifact=b.artifact(file_path="cmsis/systick.c"),
    )


def _freertos_list_insert_end() -> CorpusUnit:
    """`vListInsertEnd`-style intrusive linked-list insertion via pointer
    chasing (`pxIterator = pxIterator->pxNext`) -- the canonical case that
    needs real alias analysis to reason about, not just per-statement
    pattern matching."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "vListInsertEnd", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    decl = b.node("VarDecl", parent=body, semantic_properties={"name": "pxIterator", "has_initializer": True})
    init_member = b.node("MemberExpr", parent=decl, semantic_properties={"member": "pxIndex"})
    b.node("DeclRefExpr", parent=init_member, semantic_properties={"name": "pxList"}, essential_type="unknown")

    while_stmt = b.node("WhileStmt", parent=body)
    cond = b.node("BinaryOperator", parent=while_stmt, semantic_properties={"opcode": "!="})
    cond_member = b.node("MemberExpr", parent=cond, semantic_properties={"member": "pxNext"})
    b.node("DeclRefExpr", parent=cond_member, semantic_properties={"name": "pxIterator"}, essential_type="unknown")
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "pxNewListItem"}, essential_type="unknown")
    while_body = b.node("CompoundStmt", parent=while_stmt)
    advance = b.node("BinaryOperator", parent=while_body, semantic_properties={"opcode": "="})
    b.node("DeclRefExpr", parent=advance, semantic_properties={"name": "pxIterator"}, essential_type="unknown")
    advance_member = b.node("MemberExpr", parent=advance, semantic_properties={"member": "pxNext"})
    b.node("DeclRefExpr", parent=advance_member, semantic_properties={"name": "pxIterator"}, essential_type="unknown")

    link1 = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    link1_member = b.node("MemberExpr", parent=link1, semantic_properties={"member": "pxNext"})
    b.node("DeclRefExpr", parent=link1_member, semantic_properties={"name": "pxNewListItem"}, essential_type="unknown")
    link1_rhs = b.node("MemberExpr", parent=link1, semantic_properties={"member": "pxNext"})
    b.node("DeclRefExpr", parent=link1_rhs, semantic_properties={"name": "pxIterator"}, essential_type="unknown")

    link2 = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    link2_member = b.node("MemberExpr", parent=link2, semantic_properties={"member": "pxNext"})
    b.node("DeclRefExpr", parent=link2_member, semantic_properties={"name": "pxIterator"}, essential_type="unknown")
    b.node("DeclRefExpr", parent=link2, semantic_properties={"name": "pxNewListItem"}, essential_type="unknown")

    b.node("ReturnStmt", parent=body)

    return CorpusUnit(
        corpus="freertos",
        function_name="vListInsertEnd",
        description="Intrusive linked-list pointer-chasing insertion (aliasing-heavy).",
        known_constructs=["WhileStmt pointer-chase", "MemberExpr chain reassignment"],
        artifact=b.artifact(file_path="freertos/list.c"),
    )


def _freertos_task_delay() -> CorpusUnit:
    """`vTaskDelay`-style critical-section-guarded state update: macro-call
    pairs (`taskENTER_CRITICAL`/`taskEXIT_CRITICAL`) modeled as `CallExpr`s
    bracketing a body, plus a `for(;;)`-style scheduler idiom."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "vTaskDelay", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    b.node("CallExpr", parent=body, semantic_properties={"callee": "taskENTER_CRITICAL"})

    if_stmt = b.node("IfStmt", parent=body)
    cond = b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": ">"})
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "xTicksToDelay"}, essential_type="unsigned_long")
    b.node("IntegerLiteral", parent=cond, essential_type="signed_int", semantic_properties={"value": "0"})
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    call = b.node("CallExpr", parent=then_branch, semantic_properties={"callee": "prvAddCurrentTaskToDelayedList"})
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "xTicksToDelay"}, essential_type="unsigned_long")

    b.node("CallExpr", parent=body, semantic_properties={"callee": "taskEXIT_CRITICAL"})
    b.node("CallExpr", parent=body, semantic_properties={"callee": "portYIELD_WITHIN_API"})

    b.node("ReturnStmt", parent=body)

    return CorpusUnit(
        corpus="freertos",
        function_name="vTaskDelay",
        description="Critical-section-bracketed conditional scheduler state update.",
        known_constructs=["CallExpr macro-expansion modeling", "IfStmt guarded CallExpr"],
        artifact=b.artifact(file_path="freertos/tasks.c"),
    )


def _lwip_pbuf_header() -> CorpusUnit:
    """`pbuf_header`-style buffer-header adjustment: cast `void *payload`
    to `uint8_t *`, pointer arithmetic to move the header boundary, cast
    back to `void *` -- a canonical Rule 11.x / 18.4 pattern in network
    stacks."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "pbuf_header", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    decl = b.node("VarDecl", parent=body, essential_type="unsigned_char", semantic_properties={"name": "payload", "has_initializer": True})
    cast = b.node("CStyleCastExpr", parent=decl, essential_type="unsigned_char")
    member = b.node("MemberExpr", parent=cast, semantic_properties={"member": "payload"})
    b.node("DeclRefExpr", parent=member, semantic_properties={"name": "p"}, essential_type="unknown")

    ptr_arith = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "-="})
    b.node("DeclRefExpr", parent=ptr_arith, semantic_properties={"name": "payload"}, essential_type="unsigned_char")
    b.node("DeclRefExpr", parent=ptr_arith, semantic_properties={"name": "header_size"}, essential_type="signed_short")

    store_back = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "="})
    store_member = b.node("MemberExpr", parent=store_back, semantic_properties={"member": "payload"})
    b.node("DeclRefExpr", parent=store_member, semantic_properties={"name": "p"}, essential_type="unknown")
    cast_back = b.node("CStyleCastExpr", parent=store_back, essential_type="unknown")
    b.node("DeclRefExpr", parent=cast_back, semantic_properties={"name": "payload"}, essential_type="unsigned_char")

    b.node("ReturnStmt", parent=body)

    return CorpusUnit(
        corpus="lwip",
        function_name="pbuf_header",
        description="void* <-> uint8_t* round-trip cast with pointer arithmetic in between.",
        known_constructs=["CStyleCastExpr round-trip", "pointer -= arithmetic"],
        artifact=b.artifact(file_path="lwip/pbuf.c"),
    )


def _lwip_inet_chksum() -> CorpusUnit:
    """`inet_chksum`-style checksum accumulation loop over a raw byte
    buffer, reading through a cast `void *` pointer and returning a
    narrowed/cast result -- exercises essential-type + CFG loop analysis
    together."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "inet_chksum", "storage_class": "external"},
        essential_type="unsigned_short",
    )
    body = b.node("CompoundStmt", parent=fn)

    acc_decl = b.node("VarDecl", parent=body, essential_type="unsigned_int", semantic_properties={"name": "acc", "has_initializer": True})
    b.node("IntegerLiteral", parent=acc_decl, essential_type="unsigned_int", semantic_properties={"value": "0"})

    octet_decl = b.node("VarDecl", parent=body, essential_type="unsigned_char", semantic_properties={"name": "octetptr", "has_initializer": True})
    cast = b.node("CStyleCastExpr", parent=octet_decl, essential_type="unsigned_char")
    b.node("DeclRefExpr", parent=cast, semantic_properties={"name": "dataptr"}, essential_type="unknown")

    for_stmt = b.node("ForStmt", parent=body)
    idx = b.node("VarDecl", parent=for_stmt, essential_type="unsigned_short", semantic_properties={"name": "i", "has_initializer": True})
    b.node("IntegerLiteral", parent=idx, essential_type="unsigned_short")
    loop_cond = b.node("BinaryOperator", parent=for_stmt, semantic_properties={"opcode": "<"})
    b.node("DeclRefExpr", parent=loop_cond, semantic_properties={"name": "i"}, essential_type="unsigned_short")
    b.node("DeclRefExpr", parent=loop_cond, semantic_properties={"name": "len"}, essential_type="unsigned_short")
    incr = b.node("UnaryOperator", parent=for_stmt, semantic_properties={"opcode": "++"})
    b.node("DeclRefExpr", parent=incr, semantic_properties={"name": "i"}, essential_type="unsigned_short")
    for_body = b.node("CompoundStmt", parent=for_stmt)
    add = b.node("BinaryOperator", parent=for_body, semantic_properties={"opcode": "+="})
    b.node("DeclRefExpr", parent=add, semantic_properties={"name": "acc"}, essential_type="unsigned_int")
    subscript = b.node("ArraySubscriptExpr", parent=add)
    b.node("DeclRefExpr", parent=subscript, semantic_properties={"name": "octetptr"}, essential_type="unsigned_char")
    b.node("DeclRefExpr", parent=subscript, semantic_properties={"name": "i"}, essential_type="unsigned_short")

    ret = b.node("ReturnStmt", parent=body)
    ret_cast = b.node("CStyleCastExpr", parent=ret, essential_type="unsigned_short")
    b.node("DeclRefExpr", parent=ret_cast, semantic_properties={"name": "acc"}, essential_type="unsigned_int")

    return CorpusUnit(
        corpus="lwip",
        function_name="inet_chksum",
        description="Accumulator checksum loop over a cast byte buffer with narrowing return cast.",
        known_constructs=["ForStmt accumulation", "ArraySubscriptExpr read", "narrowing CStyleCastExpr return"],
        artifact=b.artifact(file_path="lwip/inet_chksum.c"),
    )


# Rules that are *expected* to fire purely because of how the corpus is
# built, not because of a real MISRA issue in the modeled code: every unit
# here is a single hand-built translation unit with the function defined
# directly (no separate header-declared prototype), which is exactly what
# Rule 8.4 ("compatible declaration shall be visible") flags. Real HAL/
# FreeRTOS/lwIP sources declare these in a header, so this firing is a
# corpus-construction artifact, not a genuine finding -- called out
# separately in the report rather than conflated with real findings.
KNOWN_CORPUS_ARTIFACT_RULES: dict[str, str] = {
    "misra-c2012-rule-8-4": (
        "Fires because each corpus unit is a standalone TU with the function "
        "defined directly and no separate header-declared prototype. Real "
        "HAL/FreeRTOS/lwIP sources declare these in a header; this is a "
        "corpus-modeling gap, not a genuine cross-TU linkage finding."
    ),
}


# Documented gaps: constructs genuinely present in these codebases that our
# AST schema / analyzers don't yet model at all (as opposed to modeling but
# mishandling). Distinct from `rule_capability_matrix.blocked_on_ast_metadata`
# because these are about the *corpus*, not about a specific MISRA rule.
UNSUPPORTED_CONSTRUCTS: list[dict[str, str]] = [
    {
        "construct": "Function-like macro expansion (raw, pre-expansion body)",
        "example": "NVIC_EnableIRQ(x) as written before macro expansion",
        "impact": "We model the *expanded* form; macro-body-specific rules (20.x, Dir 4.9) need the raw macro text, not covered here.",
    },
    {
        "construct": "Bit-field declarations (`unsigned int f : 3;`)",
        "example": "CMSIS peripheral bit-field structs",
        "impact": "EssentialTypeEngine.bitfield_essential_type() supports the type math; the AST schema has no bit-width metadata field yet to drive it automatically.",
    },
    {
        "construct": "Inline assembly blocks",
        "example": "CMSIS __ASM intrinsics (`__DSB()`, `__WFI()`)",
        "impact": "Not represented in the AST schema at all; Dir 4.3 (encapsulate assembly) cannot be checked.",
    },
    {
        "construct": "Volatile-qualified struct member access chains",
        "example": "`GPIOx->MODER` where MODER is declared `__IOM uint32_t`",
        "impact": "`qualifiers` is tracked per-node but our MemberExpr fixtures don't yet propagate the base struct's field qualifiers; Rule 13.2/1.3 volatile side-effect ordering checks are approximate.",
    },
    {
        "construct": "Designated initializers for peripheral config structs",
        "example": "`GPIO_InitTypeDef cfg = { .Pin = GPIO_PIN_5, .Mode = GPIO_MODE_OUTPUT_PP };`",
        "impact": "Rule 9.4/9.5 need designated-initializer metadata not yet in the AST schema (tracked in coverage_matrix.py).",
    },
]


def _stm32_hal_uart_get_state() -> CorpusUnit:
    """`HAL_UART_GetState`-style status decoder: a `switch` over a masked
    status register with every case `break`-terminated and a `default`
    last -- exercises the Phase 5 control-flow pack (16.2/16.4/16.5) plus
    a shadowed loop-scratch variable reusing an outer parameter name
    (5.3)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "HAL_UART_GetState", "storage_class": "external"},
    )
    b.node("ParmVarDecl", parent=fn, semantic_properties={"name": "state"}, line=1)
    body = b.node("CompoundStmt", parent=fn)

    switch_stmt = b.node("SwitchStmt", parent=body, line=2)
    b.node("DeclRefExpr", parent=switch_stmt, semantic_properties={"name": "state"}, line=2)
    switch_body = b.node("CompoundStmt", parent=switch_stmt)

    case_ready = b.node("CaseStmt", parent=switch_body, line=3)
    b.node("IntegerLiteral", parent=case_ready, semantic_properties={"value": "0"}, line=3)
    ret_ready = b.node("ReturnStmt", parent=switch_body, line=4)
    b.node("DeclRefExpr", parent=ret_ready, semantic_properties={"name": "HAL_UART_STATE_READY"}, line=4)
    b.node("BreakStmt", parent=switch_body, line=5)

    case_busy = b.node("CaseStmt", parent=switch_body, line=6)
    b.node("IntegerLiteral", parent=case_busy, semantic_properties={"value": "1"}, line=6)
    # Inner block shadows the outer `state` parameter with a local
    # decoded copy -- realistic, but exactly what Rule 5.3 flags.
    inner_block = b.node("CompoundStmt", parent=switch_body, line=7)
    b.node("VarDecl", parent=inner_block, semantic_properties={"name": "state"}, line=7)
    b.node("BreakStmt", parent=switch_body, line=8)

    b.node("DefaultStmt", parent=switch_body, line=9)
    ret_default = b.node("ReturnStmt", parent=switch_body, line=10)
    b.node("DeclRefExpr", parent=ret_default, semantic_properties={"name": "HAL_UART_STATE_ERROR"}, line=10)

    return CorpusUnit(
        corpus="stm32_hal",
        function_name="HAL_UART_GetState",
        description="Status-register switch decoder with break-terminated cases and a shadowed scratch variable.",
        known_constructs=["SwitchStmt with break-terminated cases", "default last", "inner-block shadowing"],
        artifact=b.artifact(file_path="stm32_hal/uart_state.c"),
    )


def _cmsis_set_priority_bounds_check() -> CorpusUnit:
    """`__NVIC_SetPriority`-style bounds validation via pointer-into-array
    relational comparison against the table's end pointer -- the Rule 18.3
    "pointers into the same object" idiom common in CMSIS priority-table
    handling, wrapped in a reserved-name-adjacent local macro alias (21.2:
    real code sometimes accidentally shadows a reserved `_`-prefixed name
    pulled in from a vendor header)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "NVIC_SetPriorityChecked", "storage_class": "static", "is_inline": True},
    )
    body = b.node("CompoundStmt", parent=fn)

    p_decl = b.node(
        "VarDecl", parent=body, type_information={"is_pointer": True}, semantic_properties={"name": "p"}, line=1
    )
    b.node("DeclRefExpr", parent=p_decl, semantic_properties={"name": "PriorityTable"}, line=1)
    end_decl = b.node(
        "VarDecl", parent=body, type_information={"is_pointer": True}, semantic_properties={"name": "end"}, line=2
    )
    b.node("DeclRefExpr", parent=end_decl, semantic_properties={"name": "PriorityTable"}, line=2)

    cmp = b.node("BinaryOperator", parent=body, semantic_properties={"opcode": "<"}, line=3)
    b.node("DeclRefExpr", parent=cmp, semantic_properties={"name": "p"}, line=3)
    b.node("DeclRefExpr", parent=cmp, semantic_properties={"name": "end"}, line=3)

    b.node("ReturnStmt", parent=body, line=4)

    return CorpusUnit(
        corpus="cmsis",
        function_name="NVIC_SetPriorityChecked",
        description="Pointer-into-same-array-object relational bounds check ahead of a priority write.",
        known_constructs=["relational comparison between pointers derived from the same base object"],
        artifact=b.artifact(file_path="cmsis/nvic_priority.c"),
    )


def _freertos_task_delete_cleanup() -> CorpusUnit:
    """`vTaskDelete`-style cleanup loop that walks a list and, on finding
    the target, both frees it and `goto`s a single shared cleanup label --
    the Rule 15.4 "no more than one break/goto to terminate a given loop"
    idiom, plus an intentionally-unused `xIndex` parameter kept only for
    ABI compatibility with an older scheduler build (Rule 2.7)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "vTaskDelete", "storage_class": "external"},
    )
    b.node("ParmVarDecl", parent=fn, semantic_properties={"name": "xTaskToDelete"}, line=1)
    b.node("ParmVarDecl", parent=fn, semantic_properties={"name": "xIndex"}, line=1)  # unused
    body = b.node("CompoundStmt", parent=fn)

    while_stmt = b.node("WhileStmt", parent=body, line=2)
    b.node("DeclRefExpr", parent=while_stmt, semantic_properties={"name": "pxIterator"}, line=2)
    loop_body = b.node("CompoundStmt", parent=while_stmt)

    if_stmt = b.node("IfStmt", parent=loop_body, line=3)
    cond = b.node("BinaryOperator", parent=if_stmt, semantic_properties={"opcode": "=="}, line=3)
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "pxIterator"}, line=3)
    b.node("DeclRefExpr", parent=cond, semantic_properties={"name": "xTaskToDelete"}, line=3)
    then_branch = b.node("CompoundStmt", parent=if_stmt)
    call = b.node("CallExpr", parent=then_branch, semantic_properties={"callee": "vPortFree"}, line=4)
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "pxIterator"}, line=4)
    b.node("GotoStmt", parent=then_branch, semantic_properties={"label": "cleanup"}, line=5)

    advance = b.node("BinaryOperator", parent=loop_body, semantic_properties={"opcode": "="}, line=6)
    b.node("DeclRefExpr", parent=advance, semantic_properties={"name": "pxIterator"}, line=6)
    member = b.node("MemberExpr", parent=advance, semantic_properties={"member": "pxNext"}, line=6)
    b.node("DeclRefExpr", parent=member, semantic_properties={"name": "pxIterator"}, line=6)

    b.node("LabelStmt", parent=body, semantic_properties={"label": "cleanup"}, line=7)
    b.node("ReturnStmt", parent=body, line=8)

    return CorpusUnit(
        corpus="freertos",
        function_name="vTaskDelete",
        description="List-walk with a single goto-to-shared-cleanup-label exit and one ABI-only unused parameter.",
        known_constructs=["WhileStmt with single GotoStmt terminator", "shared cleanup LabelStmt", "unused ParmVarDecl"],
        artifact=b.artifact(file_path="freertos/tasks_delete.c"),
    )


def _lwip_pbuf_copy_overlap() -> CorpusUnit:
    """`pbuf_copy`-style buffer duplication via `memcpy` where, on a
    misconfigured chained-pbuf edge case, the source and destination
    pointers can alias the same underlying buffer -- the Rule 19.1
    "no copy to an overlapping object" pattern network stacks must guard
    against explicitly (real lwIP uses `memcpy`, not `memmove`, here)."""
    b = Builder()
    fn = b.node(
        "FunctionDecl",
        semantic_properties={"name": "pbuf_copy", "storage_class": "external"},
    )
    body = b.node("CompoundStmt", parent=fn)

    dst_decl = b.node(
        "VarDecl", parent=body, type_information={"is_pointer": True}, semantic_properties={"name": "dst"}, line=1
    )
    addr_dst = b.node("UnaryOperator", parent=dst_decl, semantic_properties={"opcode": "&"}, line=1)
    b.node("DeclRefExpr", parent=addr_dst, semantic_properties={"name": "shared_buf"}, line=1)

    src_decl = b.node(
        "VarDecl", parent=body, type_information={"is_pointer": True}, semantic_properties={"name": "src"}, line=2
    )
    addr_src = b.node("UnaryOperator", parent=src_decl, semantic_properties={"opcode": "&"}, line=2)
    b.node("DeclRefExpr", parent=addr_src, semantic_properties={"name": "shared_buf"}, line=2)

    call = b.node("CallExpr", parent=body, semantic_properties={"callee": "memcpy"}, line=3)
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "dst"}, line=3)
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "src"}, line=3)
    b.node("DeclRefExpr", parent=call, semantic_properties={"name": "len"}, line=3)

    b.node("ReturnStmt", parent=body, line=4)

    return CorpusUnit(
        corpus="lwip",
        function_name="pbuf_copy",
        description="memcpy between two pointers both derived from the same shared buffer (aliasing hazard).",
        known_constructs=["memcpy CallExpr", "two pointer VarDecls aliasing the same base object"],
        artifact=b.artifact(file_path="lwip/pbuf_copy.c"),
    )


def build_stm32_hal_corpus() -> list[CorpusUnit]:
    return [
        _stm32_hal_gpio_write_pin(),
        _stm32_hal_uart_transmit(),
        _stm32_hal_uart_get_state(),
    ]


def build_cmsis_corpus() -> list[CorpusUnit]:
    return [
        _cmsis_nvic_enable_irq(),
        _cmsis_systick_config(),
        _cmsis_set_priority_bounds_check(),
    ]


def build_freertos_corpus() -> list[CorpusUnit]:
    return [
        _freertos_list_insert_end(),
        _freertos_task_delay(),
        _freertos_task_delete_cleanup(),
    ]


def build_lwip_corpus() -> list[CorpusUnit]:
    return [
        _lwip_pbuf_header(),
        _lwip_inet_chksum(),
        _lwip_pbuf_copy_overlap(),
    ]


def build_all_corpora() -> list[CorpusUnit]:
    return [
        *build_stm32_hal_corpus(),
        *build_cmsis_corpus(),
        *build_freertos_corpus(),
        *build_lwip_corpus(),
    ]
