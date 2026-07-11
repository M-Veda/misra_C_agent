import uuid

import pytest
from httpx import AsyncClient

from misra_platform.domain.models.analysis import AnalysisRun, Project
from misra_platform.domain.models.violations import ViolationRecord
from misra_platform.repositories.base import session_scope


async def _seed_violation(*, with_suggested_fix: bool = True) -> uuid.UUID:
    async with session_scope() as session:
        project = Project(
            name="Seed Project",
            root_path="/workspace/samples/bare-metal-stm32",
            toolchain_profile_id="clang-host",
        )
        session.add(project)
        await session.flush()

        run = AnalysisRun(project_id=project.id, run_type="full", status="completed")
        session.add(run)
        await session.flush()

        violation = ViolationRecord(
            analysis_run_id=run.id,
            project_id=project.id,
            rule_id="misra-c2012-rule-10-3",
            fingerprint="fp-" + str(uuid.uuid4()),
            file_path="/workspace/samples/bare-metal-stm32/src/rpm.c",
            line_start=10,
            line_end=10,
            column_start=1,
            column_end=20,
            severity="major",
            confidence_score=0.9,
            category="required",
            offending_expression="uint8_t narrow = wide;",
            explanation="Narrowing assignment detected.",
            risk_description="Value truncation may occur.",
            source_snippet="/workspace/samples/bare-metal-stm32/src/rpm.c:10",
            ast_node_reference="node-1",
            suggested_fix_json=(
                {
                    "original_code": "uint8_t narrow = wide;",
                    "suggested_code": "uint8_t narrow = (uint8_t)wide;",
                    "rationale": "Explicit cast documents the narrowing.",
                    "confidence_score": 0.7,
                }
                if with_suggested_fix
                else None
            ),
            status="open",
        )
        session.add(violation)
        await session.flush()
        violation_id = violation.id

    return violation_id


@pytest.mark.asyncio
async def test_accept_requires_justification(client: AsyncClient) -> None:
    violation_id = await _seed_violation()

    response = await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={"action": "accept", "reviewer_id": "eng-1"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_accept_with_justification_generates_patch(client: AsyncClient) -> None:
    violation_id = await _seed_violation()

    response = await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={
            "action": "accept",
            "reviewer_id": "eng-1",
            "reviewer_name": "Engineer One",
            "justification": "Confirmed narrowing risk after manual code inspection.",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["violation_status"] == "accepted"
    assert payload["patch"] is not None
    assert "diff --git" in payload["patch"]["git_patch"]


@pytest.mark.asyncio
async def test_reject_does_not_require_justification(client: AsyncClient) -> None:
    violation_id = await _seed_violation()

    response = await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={"action": "reject", "reviewer_id": "eng-2"},
    )
    assert response.status_code == 201
    assert response.json()["violation_status"] == "rejected"
    assert response.json()["patch"] is None


@pytest.mark.asyncio
async def test_edit_requires_edited_fix_payload(client: AsyncClient) -> None:
    violation_id = await _seed_violation()

    response = await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={"action": "edit", "reviewer_id": "eng-3"},
    )
    assert response.status_code == 422

    response = await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={
            "action": "edit",
            "reviewer_id": "eng-3",
            "edited_fix": {"suggested_code": "uint8_t narrow = (uint8_t)(wide & 0xFFU);"},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["violation_status"] == "edited"
    assert payload["patch"] is not None


@pytest.mark.asyncio
async def test_review_history_is_append_only(client: AsyncClient) -> None:
    violation_id = await _seed_violation()

    await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={"action": "skip", "reviewer_id": "eng-4"},
    )
    await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={
            "action": "suppress",
            "reviewer_id": "eng-4",
            "justification": "Suppressed after discussion with the tech lead.",
        },
    )

    history = await client.get(f"/api/v1/violations/{violation_id}/reviews")
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 2
    assert entries[0]["action"] == "skip"
    assert entries[1]["action"] == "suppress"


@pytest.mark.asyncio
async def test_bulk_skip_never_accepts(client: AsyncClient) -> None:
    violation_id_1 = await _seed_violation()
    violation_id_2 = await _seed_violation()

    response = await client.post(
        "/api/v1/violations/bulk/skip",
        json={
            "violation_ids": [str(violation_id_1), str(violation_id_2)],
            "reviewer_id": "eng-5",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload["skipped_violation_ids"]) == {str(violation_id_1), str(violation_id_2)}


@pytest.mark.asyncio
async def test_bulk_export_only_includes_approved(client: AsyncClient) -> None:
    accepted_id = await _seed_violation()
    rejected_id = await _seed_violation()

    await client.post(
        f"/api/v1/violations/{accepted_id}/reviews",
        json={
            "action": "accept",
            "reviewer_id": "eng-6",
            "justification": "Approved after validating the essential type mismatch.",
        },
    )
    await client.post(
        f"/api/v1/violations/{rejected_id}/reviews",
        json={"action": "reject", "reviewer_id": "eng-6"},
    )

    response = await client.post(
        "/api/v1/violations/bulk/export-patches",
        json={
            "violation_ids": [str(accepted_id), str(rejected_id)],
            "exported_by": "eng-6",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["exported_patch_ids"]) == 1
    assert str(rejected_id) in payload["skipped_violation_ids"]


@pytest.mark.asyncio
async def test_audit_entries_are_searchable(client: AsyncClient) -> None:
    violation_id = await _seed_violation()
    await client.post(
        f"/api/v1/violations/{violation_id}/reviews",
        json={
            "action": "false_positive",
            "reviewer_id": "eng-7",
            "justification": "Confirmed a compiler-generated implicit widening, not a real defect.",
        },
    )

    response = await client.get("/api/v1/audit-entries", params={"q": "implicit widening"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["entity_type"] == "violation"
