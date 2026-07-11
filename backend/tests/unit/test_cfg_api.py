import json
import uuid

import pytest
from httpx import AsyncClient

from misra_platform.domain.models.analysis import AnalysisRun, Project, TranslationUnitRecord
from misra_platform.repositories.base import session_scope


def _sample_ast_nodes() -> list[dict]:
    """A tiny FunctionDecl AST: `int f(void) { int x = 0; if (x) { return 1; } return 0; }`"""
    return [
        {
            "node_id": "fn1", "node_kind": "FunctionDecl", "parent_id": "", "children_ids": ["body1"],
            "source_range": {"line_start": 1, "line_end": 6}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {"name": "f"},
        },
        {
            "node_id": "body1", "node_kind": "CompoundStmt", "parent_id": "fn1",
            "children_ids": ["decl1", "if1", "ret2"],
            "source_range": {"line_start": 1, "line_end": 6}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {},
        },
        {
            "node_id": "decl1", "node_kind": "VarDecl", "parent_id": "body1", "children_ids": [],
            "source_range": {"line_start": 2, "line_end": 2}, "type_information": {}, "qualifiers": [],
            "essential_type": "signed_int", "macro_origin": {}, "semantic_properties": {"name": "x"},
        },
        {
            "node_id": "if1", "node_kind": "IfStmt", "parent_id": "body1", "children_ids": ["cond1", "then1"],
            "source_range": {"line_start": 3, "line_end": 4}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {},
        },
        {
            "node_id": "cond1", "node_kind": "DeclRefExpr", "parent_id": "if1", "children_ids": [],
            "source_range": {"line_start": 3, "line_end": 3}, "type_information": {}, "qualifiers": [],
            "essential_type": "signed_int", "macro_origin": {}, "semantic_properties": {"name": "x"},
        },
        {
            "node_id": "then1", "node_kind": "CompoundStmt", "parent_id": "if1", "children_ids": ["ret1"],
            "source_range": {"line_start": 3, "line_end": 4}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {},
        },
        {
            "node_id": "ret1", "node_kind": "ReturnStmt", "parent_id": "then1", "children_ids": [],
            "source_range": {"line_start": 3, "line_end": 3}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {},
        },
        {
            "node_id": "ret2", "node_kind": "ReturnStmt", "parent_id": "body1", "children_ids": [],
            "source_range": {"line_start": 5, "line_end": 5}, "type_information": {}, "qualifiers": [],
            "essential_type": "", "macro_origin": {}, "semantic_properties": {},
        },
    ]


async def _seed_translation_unit(tmp_path) -> tuple[uuid.UUID, uuid.UUID]:
    artifact_path = tmp_path / "tu.json"
    artifact_path.write_text(
        json.dumps({"nodes": _sample_ast_nodes(), "diagnostics": [], "preprocessor": {}}),
        encoding="utf-8",
    )

    async with session_scope() as session:
        project = Project(
            name="Seed Project", root_path="/workspace/sample", toolchain_profile_id="clang-host"
        )
        session.add(project)
        await session.flush()

        run = AnalysisRun(project_id=project.id, run_type="full", status="completed")
        session.add(run)
        await session.flush()

        tu = TranslationUnitRecord(
            analysis_run_id=run.id,
            file_path="/workspace/sample/src/f.c",
            working_directory="/workspace/sample",
            compile_flags_json=[],
            status="parsed",
            ast_cache_path=str(artifact_path),
        )
        session.add(tu)
        await session.flush()
        run_id, tu_id = run.id, tu.id

    return run_id, tu_id


@pytest.mark.asyncio
async def test_list_functions_endpoint(client: AsyncClient, tmp_path) -> None:
    run_id, tu_id = await _seed_translation_unit(tmp_path)

    response = await client.get(f"/api/v1/analysis/runs/{run_id}/translation-units/{tu_id}/functions")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["functions"]) == 1
    function = payload["functions"][0]
    assert function["function_node_id"] == "fn1"
    assert function["name"] == "f"
    assert function["has_body"] is True


@pytest.mark.asyncio
async def test_get_function_cfg_endpoint(client: AsyncClient, tmp_path) -> None:
    run_id, tu_id = await _seed_translation_unit(tmp_path)

    response = await client.get(
        f"/api/v1/analysis/runs/{run_id}/translation-units/{tu_id}/functions/fn1/cfg"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["function_node_id"] == "fn1"
    assert len(payload["blocks"]) >= 3
    edge_kinds = {edge["kind"] for edge in payload["edges"]}
    assert "true" in edge_kinds
    assert "false" in edge_kinds
    assert payload["dot"] is None


@pytest.mark.asyncio
async def test_get_function_cfg_with_dot(client: AsyncClient, tmp_path) -> None:
    run_id, tu_id = await _seed_translation_unit(tmp_path)

    response = await client.get(
        f"/api/v1/analysis/runs/{run_id}/translation-units/{tu_id}/functions/fn1/cfg",
        params={"include_dot": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["dot"] is not None
    assert "digraph CFG" in payload["dot"]


@pytest.mark.asyncio
async def test_get_function_cfg_unknown_function_returns_404(client: AsyncClient, tmp_path) -> None:
    run_id, tu_id = await _seed_translation_unit(tmp_path)

    response = await client.get(
        f"/api/v1/analysis/runs/{run_id}/translation-units/{tu_id}/functions/does-not-exist/cfg"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_translation_unit_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        f"/api/v1/analysis/runs/{uuid.uuid4()}/translation-units/{uuid.uuid4()}/functions"
    )
    assert response.status_code == 404
