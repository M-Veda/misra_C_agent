import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from misra_platform.domain.enums.review_action import ReviewAction


class EditedFixPayload(BaseModel):
    original_code: str = ""
    suggested_code: str
    rationale: str = ""
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


class ReviewActionRequest(BaseModel):
    action: ReviewAction
    reviewer_id: str = Field(min_length=1, max_length=128)
    reviewer_name: str | None = Field(default=None, max_length=255)
    justification: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)
    edited_fix: EditedFixPayload | None = None

    @field_validator("reviewer_id")
    @classmethod
    def strip_reviewer_id(cls, value: str) -> str:
        return value.strip()


class ViolationReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    violation_id: uuid.UUID
    action: str
    previous_status: str
    new_status: str
    reviewer_id: str
    reviewer_name: str | None
    justification: str | None
    notes: str | None
    edited_fix_json: dict | None
    created_at: datetime


class PatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    violation_id: uuid.UUID
    review_id: uuid.UUID
    file_path: str
    unified_diff: str
    git_patch: str
    source_available: bool
    confidence_score: float
    status: str
    created_by: str
    created_at: datetime
    exported_at: datetime | None
    exported_by: str | None


class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    actor_name: str | None
    old_state_json: dict | None
    new_state_json: dict | None
    justification: str | None
    notes: str | None
    created_at: datetime


class SubmitReviewResponse(BaseModel):
    review: ViolationReviewResponse
    audit_entry: AuditEntryResponse
    patch: PatchResponse | None
    violation_status: str


class SourceWindowResponse(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    lines: list[str]
    highlight_start: int
    highlight_end: int
    available: bool


class ImpactEstimateResponse(BaseModel):
    level: str
    score: float
    summary: str


class BulkSkipRequest(BaseModel):
    violation_ids: list[uuid.UUID] = Field(min_length=1)
    reviewer_id: str = Field(min_length=1, max_length=128)
    reviewer_name: str | None = None
    notes: str | None = None


class BulkSkipResponse(BaseModel):
    skipped_violation_ids: list[uuid.UUID]
    not_found_violation_ids: list[uuid.UUID]


class BulkAssignReviewerRequest(BaseModel):
    violation_ids: list[uuid.UUID] = Field(min_length=1)
    reviewer_id: str = Field(min_length=1, max_length=128)
    reviewer_name: str | None = None
    assigned_by: str = Field(min_length=1, max_length=128)


class BulkAssignReviewerResponse(BaseModel):
    assigned_violation_ids: list[uuid.UUID]
    not_found_violation_ids: list[uuid.UUID]


class BulkExportPatchesRequest(BaseModel):
    violation_ids: list[uuid.UUID] = Field(min_length=1)
    exported_by: str = Field(min_length=1, max_length=128)


class BulkExportPatchesResponse(BaseModel):
    combined_patch: str
    exported_patch_ids: list[uuid.UUID]
    skipped_violation_ids: list[uuid.UUID]
