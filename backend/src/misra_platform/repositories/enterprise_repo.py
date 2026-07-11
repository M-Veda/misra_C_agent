import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.domain.models.enterprise import (
    ComplianceSnapshotRecord,
    IntegrationConfigRecord,
    TeamMemberRecord,
    TeamRecord,
)
from misra_platform.domain.models.review import AuditEntryRecord
from misra_platform.domain.models.violations import ViolationRecord


class EnterpriseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_violation(self, violation_id: uuid.UUID) -> ViolationRecord | None:
        return await self.session.get(ViolationRecord, violation_id)

    async def create_team(self, team: TeamRecord) -> TeamRecord:
        self.session.add(team)
        await self.session.flush()
        return team

    async def get_team(self, team_id: uuid.UUID) -> TeamRecord | None:
        return await self.session.get(TeamRecord, team_id)

    async def list_teams(self) -> list[TeamRecord]:
        result = await self.session.execute(select(TeamRecord).order_by(TeamRecord.name.asc()))
        return list(result.scalars().all())

    async def add_team_member(self, member: TeamMemberRecord) -> TeamMemberRecord:
        self.session.add(member)
        await self.session.flush()
        return member

    async def list_team_members(self, team_id: uuid.UUID) -> list[TeamMemberRecord]:
        result = await self.session.execute(
            select(TeamMemberRecord)
            .where(TeamMemberRecord.team_id == team_id)
            .order_by(TeamMemberRecord.display_name.asc())
        )
        return list(result.scalars().all())

    async def get_team_member(self, team_id: uuid.UUID, user_id: str) -> TeamMemberRecord | None:
        result = await self.session.execute(
            select(TeamMemberRecord).where(
                TeamMemberRecord.team_id == team_id,
                TeamMemberRecord.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def save_snapshot(self, snapshot: ComplianceSnapshotRecord) -> ComplianceSnapshotRecord:
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def list_snapshots(
        self,
        *,
        project_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ComplianceSnapshotRecord]:
        query = select(ComplianceSnapshotRecord).where(
            ComplianceSnapshotRecord.project_id == project_id
        )
        if team_id:
            query = query.where(ComplianceSnapshotRecord.team_id == team_id)
        query = query.order_by(ComplianceSnapshotRecord.captured_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_integration_config(
        self, project_id: uuid.UUID, provider: str
    ) -> IntegrationConfigRecord | None:
        result = await self.session.execute(
            select(IntegrationConfigRecord).where(
                IntegrationConfigRecord.project_id == project_id,
                IntegrationConfigRecord.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_integration_config(
        self, config: IntegrationConfigRecord
    ) -> IntegrationConfigRecord:
        self.session.add(config)
        await self.session.flush()
        return config

    async def append_audit(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_id: str,
        actor_name: str | None,
        new_state: dict | None = None,
        old_state: dict | None = None,
        notes: str | None = None,
    ) -> AuditEntryRecord:
        entry = AuditEntryRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            actor_name=actor_name,
            old_state_json=old_state,
            new_state_json=new_state,
            notes=notes,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry
