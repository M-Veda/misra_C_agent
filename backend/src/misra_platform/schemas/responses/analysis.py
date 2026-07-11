import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    root_path: str
    toolchain_profile_id: str = "clang-host"
    compile_commands_path: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    root_path: str
    toolchain_profile_id: str
    compile_commands_path: str | None
    created_at: datetime
    updated_at: datetime


class AnalysisRunCreateRequest(BaseModel):
    run_type: Literal["full", "incremental"] = "full"
    base_run_id: uuid.UUID | None = None


class AnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    run_type: str
    status: str
    files_total: int
    files_parsed: int
    files_failed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TranslationUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_run_id: uuid.UUID
    file_path: str
    status: str
    translation_unit_hash: str | None
    node_count: int
    parse_duration_ms: int
    diagnostics_json: list | None
    preprocessor_json: dict | None
    error_message: str | None


class AstNodeResponse(BaseModel):
    node_id: str
    node_kind: str
    parent_id: str
    children_ids: list[str]
    source_range: dict
    type_information: dict
    qualifiers: list[str]
    essential_type: str
    macro_origin: dict
    semantic_properties: dict


class AstArtifactResponse(BaseModel):
    translation_unit_id: uuid.UUID
    file_path: str
    translation_unit_hash: str
    nodes: list[AstNodeResponse]
    diagnostics: list[dict]
    preprocessor: dict
