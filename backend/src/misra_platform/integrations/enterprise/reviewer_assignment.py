"""Reviewer assignment for multi-user compliance workflow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from misra_platform.domain.models.enterprise import TeamMemberRecord
from misra_platform.domain.models.review import AuditEntryRecord
from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.repositories.enterprise_repo import EnterpriseRepository


class ReviewerAssignmentError(Exception):
    pass


@dataclass(slots=True)
class AssignmentOutcome:
    violation: ViolationRecord
    audit_entry: AuditEntryRecord


class ReviewerAssignmentService:
    def __init__(self, repo: EnterpriseRepository) -> None:
        self.repo = repo

    async def assign_reviewer(
        self,
        violation: ViolationRecord,
        *,
        reviewer_id: str,
        reviewer_name: str,
        actor_id: str,
        actor_name: str,
        team_id: uuid.UUID | None = None,
    ) -> AssignmentOutcome:
        if team_id:
            member = await self.repo.get_team_member(team_id, reviewer_id)
            if not member:
                raise ReviewerAssignmentError(
                    f"Reviewer '{reviewer_id}' is not a member of team '{team_id}'."
                )

        violation.assigned_reviewer_id = reviewer_id
        violation.assigned_reviewer_name = reviewer_name

        audit = await self.repo.append_audit(
            entity_type="violation",
            entity_id=str(violation.id),
            action="reviewer_assigned",
            actor_id=actor_id,
            actor_name=actor_name,
            new_state={
                "reviewer_id": reviewer_id,
                "reviewer_name": reviewer_name,
                "team_id": str(team_id) if team_id else None,
                "rule_id": violation.rule_id,
                "file_path": violation.file_path,
            },
        )
        return AssignmentOutcome(violation=violation, audit_entry=audit)

    async def auto_assign_round_robin(
        self,
        violations: list[ViolationRecord],
        team_id: uuid.UUID,
        *,
        actor_id: str,
        actor_name: str,
    ) -> list[AssignmentOutcome]:
        members: list[TeamMemberRecord] = await self.repo.list_team_members(team_id)
        if not members:
            raise ReviewerAssignmentError(f"Team '{team_id}' has no members.")

        outcomes: list[AssignmentOutcome] = []
        for index, violation in enumerate(violations):
            member = members[index % len(members)]
            outcome = await self.assign_reviewer(
                violation,
                reviewer_id=member.user_id,
                reviewer_name=member.display_name,
                actor_id=actor_id,
                actor_name=actor_name,
                team_id=team_id,
            )
            outcomes.append(outcome)
        return outcomes

    async def bulk_assign(
        self,
        violation_ids: list[uuid.UUID],
        *,
        reviewer_id: str,
        reviewer_name: str,
        actor_id: str,
        actor_name: str,
        team_id: uuid.UUID | None = None,
    ) -> list[AssignmentOutcome]:
        outcomes: list[AssignmentOutcome] = []
        for violation_id in violation_ids:
            violation = await self.repo.get_violation(violation_id)
            if not violation:
                continue
            outcomes.append(
                await self.assign_reviewer(
                    violation,
                    reviewer_id=reviewer_id,
                    reviewer_name=reviewer_name,
                    actor_id=actor_id,
                    actor_name=actor_name,
                    team_id=team_id,
                )
            )
        return outcomes
