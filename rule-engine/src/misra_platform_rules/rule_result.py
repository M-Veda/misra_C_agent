from pydantic import BaseModel, Field


class RuleMetadata(BaseModel):
    rule_id: str
    rule_number: str
    standard: str
    category: str
    severity: str
    title: str
    description: str
    rationale: str
    tags: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    plugin_module: str
    plugin_version: str = "0.1.0"
    requires_ast_nodes: list[str] = Field(default_factory=list)

    # Phase 3 taxonomy / dependency graph fields. Defaulted so Phase 1.2 rules
    # remain valid without modification.
    implementation_category: str = "A_ast_only"
    rule_pack: str | None = None
    requires_type_info: bool = False
    requires_cfg: bool = False
    requires_dataflow: bool = False
    requires_linkage: bool = False
    requires_macro_expansion: bool = False
    rule_dependencies: list[str] = Field(default_factory=list)


class RuleExamples(BaseModel):
    compliant: list[str] = Field(default_factory=list)
    non_compliant: list[str] = Field(default_factory=list)


class SuggestedFix(BaseModel):
    original_code: str
    suggested_code: str
    rationale: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class RuleResult(BaseModel):
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    offending_expression: str
    explanation: str
    risk_description: str
    source_snippet: str
    ast_node_id: str
    ast_node_path: list[str]
    macro_expansion_chain: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    suggested_fix: SuggestedFix | None = None
    confidence_factors: dict[str, float] = Field(default_factory=dict)
