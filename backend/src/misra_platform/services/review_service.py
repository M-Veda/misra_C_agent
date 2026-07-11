"""Human-in-the-loop review workflow orchestration.

This service NEVER writes to source files and NEVER auto-applies a fix.
Every violation must pass through an explicit engineer action. All review
and audit rows are append-only — this service only ever INSERTs them.
"""

from dataclasses import dataclass

from misra_platform.domain.enums.review_action import (
    ACTION_TO_STATUS,
    ACTIONS_GENERATING_PATCHES,
    ACTIONS_REQUIRING_JUSTIFICATION,
    MIN_JUSTIFICATION_LENGTH,
    ReviewAction,
)
from misra_platform.domain.models.review import AuditEntryRecord, PatchRecord, ViolationReviewRecord
from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.repositories.review_repo import ReviewRepository
from misra_platform.services.patch_engine import PatchEngine


class ReviewValidationError(Exception):
    pass


class ViolationNotFoundError(Exception):
    pass


@dataclass(slots=True)
class ReviewOutcome:
    review: ViolationReviewRecord
    audit_entry: AuditEntryRecord
    patch: PatchRecord | None


def estimate_impact(violation: ViolationRecord) -> dict:
    """Simple, explainable heuristic — never a hidden black box."""
    severity_weight = {"critical": 1.0, "major": 0.75, "minor": 0.4, "info": 0.15}.get(
        violation.severity, 0.5
    )
    category_weight = {"mandatory": 1.0, "required": 0.7, "advisory": 0.4}.get(
        violation.category, 0.5
    )
    score = round((severity_weight * 0.6 + category_weight * 0.25 + violation.confidence_score * 0.15), 2)
    if score >= 0.75:
        level = "high"
    elif score >= 0.45:
        level = "medium"
    else:
        level = "low"
    return {
        "level": level,
        "score": score,
        "summary": (
            f"{violation.severity.title()} severity, {violation.category} rule, "
            f"{round(violation.confidence_score * 100)}% detection confidence."
        ),
    }


class ReviewService:
    def __init__(self, repo: ReviewRepository, patch_engine: PatchEngine | None = None) -> None:
        self.repo = repo
        self.patch_engine = patch_engine or PatchEngine()

    def _validate_justification(self, action: ReviewAction, justification: str | None) -> None:
        if action not in ACTIONS_REQUIRING_JUSTIFICATION:
            return
        if not justification or len(justification.strip()) < MIN_JUSTIFICATION_LENGTH:
            raise ReviewValidationError(
                f"Action '{action}' requires a justification of at least "
                f"{MIN_JUSTIFICATION_LENGTH} characters."
            )

    def _resolve_fix_text(
        self,
        action: ReviewAction,
        violation: ViolationRecord,
        edited_fix: dict | None,
    ) -> str | None:
        if action == ReviewAction.EDIT:
            if not edited_fix or not edited_fix.get("suggested_code"):
                raise ReviewValidationError("Edit action requires 'edited_fix.suggested_code'.")
            return str(edited_fix["suggested_code"])
        if action == ReviewAction.ACCEPT:
            fix = violation.suggested_fix_json or {}
            return fix.get("suggested_code")
        return None

    async def submit_review(
        self,
        *,
        violation: ViolationRecord,
        project_root: str,
        action: ReviewAction,
        reviewer_id: str,
        reviewer_name: str | None,
        justification: str | None,
        notes: str | None,
        edited_fix: dict | None = None,
    ) -> ReviewOutcome:
        self._validate_justification(action, justification)
        fix_text = self._resolve_fix_text(action, violation, edited_fix)

        previous_status = violation.status
        new_status = ACTION_TO_STATUS[action]

        review = ViolationReviewRecord(
            violation_id=violation.id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            justification=justification,
            notes=notes,
            edited_fix_json=edited_fix if action == ReviewAction.EDIT else None,
        )
        await self.repo.add_review(review)

        violation.status = new_status
        await self.repo.session.flush()

        audit_entry = AuditEntryRecord(
            entity_type="violation",
            entity_id=str(violation.id),
            action=f"review.{action}",
            actor_id=reviewer_id,
            actor_name=reviewer_name,
            old_state_json={"status": previous_status},
            new_state_json={"status": new_status, "review_id": str(review.id)},
            justification=justification,
            notes=notes,
        )
        await self.repo.add_audit_entry(audit_entry)

        patch: PatchRecord | None = None
        if action in ACTIONS_GENERATING_PATCHES and fix_text:
            generated = self.patch_engine.generate(
                project_root=project_root,
                file_path=violation.file_path,
                line_start=violation.line_start,
                line_end=violation.line_end,
                fix_text=fix_text,
                offending_expression=violation.offending_expression,
            )
            patch = PatchRecord(
                violation_id=violation.id,
                review_id=review.id,
                file_path=violation.file_path,
                unified_diff=generated.unified_diff,
                git_patch=generated.git_patch,
                source_available=generated.source_available,
                confidence_score=violation.confidence_score,
                status="generated",
                created_by=reviewer_id,
            )
            await self.repo.add_patch(patch)

            patch_audit = AuditEntryRecord(
                entity_type="patch",
                entity_id=str(patch.id),
                action="patch.generated",
                actor_id=reviewer_id,
                actor_name=reviewer_name,
                old_state_json=None,
                new_state_json={"violation_id": str(violation.id), "review_id": str(review.id)},
                justification=None,
                notes="Patch generated for export. No automatic apply operation exists.",
            )
            await self.repo.add_audit_entry(patch_audit)

        return ReviewOutcome(review=review, audit_entry=audit_entry, patch=patch)

    async def assign_reviewer(
        self,
        *,
        violation: ViolationRecord,
        reviewer_id: str,
        reviewer_name: str | None,
        assigned_by: str,
    ) -> AuditEntryRecord:
        old_state = {
            "assigned_reviewer_id": violation.assigned_reviewer_id,
            "assigned_reviewer_name": violation.assigned_reviewer_name,
        }
        violation.assigned_reviewer_id = reviewer_id
        violation.assigned_reviewer_name = reviewer_name
        await self.repo.session.flush()

        audit_entry = AuditEntryRecord(
            entity_type="violation",
            entity_id=str(violation.id),
            action="assign_reviewer",
            actor_id=assigned_by,
            actor_name=None,
            old_state_json=old_state,
            new_state_json={
                "assigned_reviewer_id": reviewer_id,
                "assigned_reviewer_name": reviewer_name,
            },
            justification=None,
            notes=None,
        )
        return await self.repo.add_audit_entry(audit_entry)
