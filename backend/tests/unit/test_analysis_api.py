import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project_and_start_analysis(client: AsyncClient) -> None:
    project_response = await client.post(
        "/api/v1/projects",
        json={
            "name": "STM32 Sample",
            "root_path": "/workspace/samples/bare-metal-stm32",
            "toolchain_profile_id": "clang-host",
            "compile_commands_path": "/workspace/samples/bare-metal-stm32/compile_commands.json",
        },
    )

    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    with patch(
        "misra_platform.api.v1.analysis.AnalysisOrchestrator.run_analysis",
        new=AsyncMock(),
    ):
        run_response = await client.post(
            f"/api/v1/projects/{project_id}/analysis/runs",
            json={"run_type": "full"},
        )

    assert run_response.status_code == 202
    assert run_response.json()["status"] == "queued"
    uuid.UUID(run_response.json()["id"])
