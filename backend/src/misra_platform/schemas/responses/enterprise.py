import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    user_id: str
    display_name: str
    email: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    members: list[TeamMemberResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ComplianceSnapshotResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    analysis_run_id: uuid.UUID
    team_id: uuid.UUID | None
    violations_total: int
    violations_open: int
    violations_resolved: int
    rules_executed: int
    compliance_score: float
    metrics_json: dict | None
    captured_at: datetime

    model_config = {"from_attributes": True}


class TeamDashboardResponse(BaseModel):
    project_id: uuid.UUID
    team_id: uuid.UUID | None
    violations_open: int
    violations_resolved: int
    violations_total: int
    compliance_score: float
    rules_executed: int
    assigned_pending: int
    trend_direction: str


class ComplianceTrendPoint(BaseModel):
    captured_at: str
    analysis_run_id: str
    violations_total: int
    violations_open: int
    violations_resolved: int
    compliance_score: float
    rules_executed: int
    metrics: dict | None = None


class PrCommentResponse(BaseModel):
    body: str
    inline_comments: list[dict] = Field(default_factory=list)


class JiraSyncResponse(BaseModel):
    issues_created: int
    results: list[dict]


class ReviewerAssignmentResponse(BaseModel):
    violation_id: uuid.UUID
    assigned_reviewer_id: str
    assigned_reviewer_name: str
    audit_entry_id: uuid.UUID
