import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RuleMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    implementation_category: str = "A_ast_only"
    rule_pack: str | None = None
    requires_type_info: bool = False
    requires_cfg: bool = False
    requires_dataflow: bool = False
    requires_linkage: bool = False
    requires_macro_expansion: bool = False
    rule_dependencies: list[str] = Field(default_factory=list)


class RuleExamplesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    compliant: list[str] = Field(default_factory=list)
    non_compliant: list[str] = Field(default_factory=list)


class RuleDetailResponse(RuleMetadataResponse):
    examples: RuleExamplesResponse = Field(default_factory=RuleExamplesResponse)


class RuleCoverageResponse(BaseModel):
    total_rules: int
    by_standard: dict[str, int]
    by_category: dict[str, int]
    implemented_rule_ids: list[str]


class CoverageMatrixEntryResponse(BaseModel):
    identifier: str
    kind: str
    title: str
    category: str
    rule_pack: str | None
    misra_class: str
    implemented: bool
    implemented_rule_id: str | None
    unsupported_reason: str | None


class CoverageMatrixResponse(BaseModel):
    summary: dict[str, int]
    entries: list[CoverageMatrixEntryResponse]


class RoadmapCapabilitiesResponse(BaseModel):
    ast_only: bool
    type_system: bool
    cfg: bool
    dataflow: bool
    linkage: bool
    alias_analysis: bool


class RoadmapEntryResponse(BaseModel):
    identifier: str
    title: str
    misra_class: str
    capabilities: RoadmapCapabilitiesResponse
    tier: str
    reason: str | None


class ImplementationRoadmapResponse(BaseModel):
    summary: dict[str, int]
    entries: list[RoadmapEntryResponse]


class SuggestedFixResponse(BaseModel):
    original_code: str
    suggested_code: str
    rationale: str
    confidence_score: float


class ViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_run_id: uuid.UUID
    translation_unit_id: uuid.UUID | None
    project_id: uuid.UUID
    rule_id: str
    fingerprint: str
    file_path: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    severity: str
    confidence_score: float
    category: str
    offending_expression: str
    explanation: str
    risk_description: str
    source_snippet: str
    ast_node_reference: str
    macro_expansion_chain_json: list | None
    suggested_fix_json: dict | None
    confidence_factors_json: dict | None
    status: str
    assigned_reviewer_id: str | None = None
    assigned_reviewer_name: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class RuleRunStatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_run_id: uuid.UUID
    rules_executed: int
    violations_total: int
    violations_deduplicated: int
    execution_duration_ms: float
    translation_units_analyzed: int
    metrics_json: dict | None
