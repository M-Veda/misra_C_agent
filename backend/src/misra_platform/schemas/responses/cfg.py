from pydantic import BaseModel, Field


class CfgFunctionSummaryResponse(BaseModel):
    function_node_id: str
    name: str
    has_body: bool
    line_start: int | None = None
    line_end: int | None = None


class CfgFunctionListResponse(BaseModel):
    translation_unit_id: str
    functions: list[CfgFunctionSummaryResponse]


class CfgBasicBlockResponse(BaseModel):
    block_id: str
    kind: str
    statement_node_ids: list[str | None] = Field(default_factory=list)
    statement_kinds: list[str | None] = Field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None


class CfgEdgeResponse(BaseModel):
    source: str
    target: str
    kind: str
    label: str | None = None


class ControlFlowGraphResponse(BaseModel):
    function_node_id: str
    entry_block_id: str
    exit_block_id: str
    blocks: list[CfgBasicBlockResponse]
    edges: list[CfgEdgeResponse]
    unreachable_block_ids: list[str]
    dot: str | None = None
