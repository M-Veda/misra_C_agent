import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from misra_platform.domain.models.analysis import Project
from misra_platform.domain.models.review import AuditEntryRecord, PatchRecord, ViolationReviewRecord
from misra_platform.domain.models.violations import ViolationRecord


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_violation(self, violation_id: uuid.UUID) -> ViolationRecord | None:
        return await self.session.get(ViolationRecord, violation_id)

    async def get_project_root(self, project_id: uuid.UUID) -> str:
        project = await self.session.get(Project, project_id)
        return project.root_path if project else ""

    async def add_review(self, review: ViolationReviewRecord) -> ViolationReviewRecord:
        self.session.add(review)
        await self.session.flush()
        return review

    async def add_audit_entry(self, entry: AuditEntryRecord) -> AuditEntryRecord:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def add_patch(self, patch: PatchRecord) -> PatchRecord:
        self.session.add(patch)
        await self.session.flush()
        return patch

    async def list_reviews(self, violation_id: uuid.UUID) -> list[ViolationReviewRecord]:
        result = await self.session.execute(
            select(ViolationReviewRecord)
            .where(ViolationReviewRecord.violation_id == violation_id)
            .order_by(ViolationReviewRecord.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_patches(self, violation_id: uuid.UUID) -> list[PatchRecord]:
        result = await self.session.execute(
            select(PatchRecord)
            .where(PatchRecord.violation_id == violation_id)
            .order_by(PatchRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_patch(self, patch_id: uuid.UUID) -> PatchRecord | None:
        return await self.session.get(PatchRecord, patch_id)

    async def list_patches_by_ids(self, violation_ids: list[uuid.UUID]) -> list[PatchRecord]:
        if not violation_ids:
            return []
        result = await self.session.execute(
            select(PatchRecord)
            .where(PatchRecord.violation_id.in_(violation_ids))
            .order_by(PatchRecord.violation_id.asc(), PatchRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_patch_exported(self, patch: PatchRecord, exported_by: str) -> PatchRecord:
        patch.status = "exported"
        patch.exported_at = datetime.now(UTC)
        patch.exported_by = exported_by
        await self.session.flush()
        return patch

    async def search_audit_entries(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        actor_id: str | None = None,
        search_text: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntryRecord]:
        query = select(AuditEntryRecord)
        if entity_type:
            query = query.where(AuditEntryRecord.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditEntryRecord.entity_id == entity_id)
        if action:
            query = query.where(AuditEntryRecord.action == action)
        if actor_id:
            query = query.where(AuditEntryRecord.actor_id == actor_id)
        if search_text:
            like_pattern = f"%{search_text}%"
            query = query.where(
                (AuditEntryRecord.justification.ilike(like_pattern))
                | (AuditEntryRecord.notes.ilike(like_pattern))
            )
        query = query.order_by(AuditEntryRecord.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
