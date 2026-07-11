import uuid

from pydantic import BaseModel, Field


class CreateTeamRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class AddTeamMemberRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    role: str = Field(default="reviewer", max_length=64)


class AssignReviewerRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=128)
    reviewer_name: str = Field(min_length=1, max_length=255)
    actor_id: str = Field(min_length=1, max_length=128)
    actor_name: str | None = Field(default=None, max_length=255)
    team_id: uuid.UUID | None = None


class BulkAssignReviewersRequest(BaseModel):
    violation_ids: list[uuid.UUID] = Field(min_length=1)
    reviewer_id: str = Field(min_length=1, max_length=128)
    reviewer_name: str = Field(min_length=1, max_length=255)
    actor_id: str = Field(min_length=1, max_length=128)
    actor_name: str | None = Field(default=None, max_length=255)
    team_id: uuid.UUID | None = None


class RoundRobinAssignRequest(BaseModel):
    run_id: uuid.UUID
    team_id: uuid.UUID
    actor_id: str = Field(min_length=1, max_length=128)
    actor_name: str | None = Field(default=None, max_length=255)


class PrCommentRequest(BaseModel):
    platform: str = Field(default="github", pattern="^(github|gitlab)$")
    max_inline_comments: int = Field(default=50, ge=0, le=100)


class JiraSyncRequest(BaseModel):
    base_url: str = Field(min_length=1)
    email: str = Field(min_length=1)
    api_token: str = Field(min_length=1)
    project_key: str = Field(min_length=1, max_length=32)
    actor_id: str = Field(min_length=1, max_length=128)
    actor_name: str | None = Field(default=None, max_length=255)
    max_issues: int = Field(default=25, ge=1, le=100)


class CaptureSnapshotRequest(BaseModel):
    team_id: uuid.UUID | None = None
