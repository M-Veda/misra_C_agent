"""Bulk review operations.

Intentionally excludes bulk-accept: every acceptance of a suggested fix must
be an individual, deliberate engineer decision with its own justification.
"""

import uuid
from dataclasses import dataclass, field

from misra_platform.domain.enums.review_action import ReviewAction
from misra_platform.domain.enums.violation_status import ViolationStatus
from misra_platform.domain.models.review import AuditEntryRecord, PatchRecord
from misra_platform.repositories.review_repo import ReviewRepository
from misra_platform.services.review_service import ReviewOutcome, ReviewService


@dataclass(slots=True)
class BulkSkipResult:
    outcomes: list[ReviewOutcome] = field(default_factory=list)
    skipped_violation_ids: list[uuid.UUID] = field(default_factory=list)
    not_found_violation_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(slots=True)
class BulkAssignResult:
    assigned_violation_ids: list[uuid.UUID] = field(default_factory=list)
    not_found_violation_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass(slots=True)
class BulkExportResult:
    combined_patch: str
    exported_patch_ids: list[uuid.UUID]
    skipped_violation_ids: list[uuid.UUID]


class BulkReviewService:
    def __init__(self, repo: ReviewRepository, review_service: ReviewService) -> None:
        self.repo = repo
        self.review_service = review_service

    async def bulk_skip(
        self,
        *,
        violation_ids: list[uuid.UUID],
        reviewer_id: str,
        reviewer_name: str | None,
        notes: str | None,
    ) -> BulkSkipResult:
        result = BulkSkipResult()
        for violation_id in violation_ids:
            violation = await self.repo.get_violation(violation_id)
            if not violation:
                result.not_found_violation_ids.append(violation_id)
                continue
            project_root = await self.repo.get_project_root(violation.project_id)
            outcome = await self.review_service.submit_review(
                violation=violation,
                project_root=project_root,
                action=ReviewAction.SKIP,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                justification=None,
                notes=notes,
            )
            result.outcomes.append(outcome)
            result.skipped_violation_ids.append(violation_id)

        await self.repo.add_audit_entry(
            AuditEntryRecord(
                entity_type="bulk_operation",
                entity_id=f"bulk-skip-{uuid.uuid4()}",
                action="bulk_skip",
                actor_id=reviewer_id,
                actor_name=reviewer_name,
                old_state_json=None,
                new_state_json={"violation_ids": [str(v) for v in result.skipped_violation_ids]},
                justification=None,
                notes=notes,
            )
        )
        return result

    async def bulk_assign_reviewer(
        self,
        *,
        violation_ids: list[uuid.UUID],
        reviewer_id: str,
        reviewer_name: str | None,
        assigned_by: str,
    ) -> BulkAssignResult:
        result = BulkAssignResult()
        for violation_id in violation_ids:
            violation = await self.repo.get_violation(violation_id)
            if not violation:
                result.not_found_violation_ids.append(violation_id)
                continue
            await self.review_service.assign_reviewer(
                violation=violation,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                assigned_by=assigned_by,
            )
            result.assigned_violation_ids.append(violation_id)

        await self.repo.add_audit_entry(
            AuditEntryRecord(
                entity_type="bulk_operation",
                entity_id=f"bulk-assign-{uuid.uuid4()}",
                action="bulk_assign_reviewer",
                actor_id=assigned_by,
                actor_name=None,
                old_state_json=None,
                new_state_json={
                    "violation_ids": [str(v) for v in result.assigned_violation_ids],
                    "reviewer_id": reviewer_id,
                    "reviewer_name": reviewer_name,
                },
                justification=None,
                notes=None,
            )
        )
        return result

    async def bulk_export_approved_patches(
        self,
        *,
        violation_ids: list[uuid.UUID],
        exported_by: str,
    ) -> BulkExportResult:
        approved_statuses = {ViolationStatus.ACCEPTED, ViolationStatus.EDITED}
        eligible_ids: list[uuid.UUID] = []
        skipped_ids: list[uuid.UUID] = []

        for violation_id in violation_ids:
            violation = await self.repo.get_violation(violation_id)
            if not violation or violation.status not in approved_statuses:
                skipped_ids.append(violation_id)
                continue
            eligible_ids.append(violation_id)

        all_patches = await self.repo.list_patches_by_ids(eligible_ids)
        latest_patch_by_violation: dict[uuid.UUID, PatchRecord] = {}
        for patch in all_patches:
            if patch.violation_id not in latest_patch_by_violation:
                latest_patch_by_violation[patch.violation_id] = patch

        exported_ids: list[uuid.UUID] = []
        patch_bodies: list[str] = []
        for violation_id in eligible_ids:
            patch = latest_patch_by_violation.get(violation_id)
            if not patch:
                skipped_ids.append(violation_id)
                continue
            await self.repo.mark_patch_exported(patch, exported_by)
            exported_ids.append(patch.id)
            patch_bodies.append(patch.git_patch)

        combined_patch = "\n".join(patch_bodies)

        await self.repo.add_audit_entry(
            AuditEntryRecord(
                entity_type="bulk_operation",
                entity_id=f"bulk-export-{uuid.uuid4()}",
                action="bulk_export_patches",
                actor_id=exported_by,
                actor_name=None,
                old_state_json=None,
                new_state_json={"patch_ids": [str(p) for p in exported_ids]},
                justification=None,
                notes="Export only. No patches were applied automatically.",
            )
        )

        return BulkExportResult(
            combined_patch=combined_patch,
            exported_patch_ids=exported_ids,
            skipped_violation_ids=skipped_ids,
        )
