import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rule_catalog_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 36
    assert any(item["rule_number"] == "8.4" for item in payload)


@pytest.mark.asyncio
async def test_rule_detail_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/catalog/misra-c2012-rule-10-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rule_id"] == "misra-c2012-rule-10-1"
    assert "examples" in payload


@pytest.mark.asyncio
async def test_rule_coverage_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/catalog/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_rules"] >= 36


@pytest.mark.asyncio
async def test_rule_coverage_matrix_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/catalog/coverage-matrix")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_rules"] >= 140
    assert payload["summary"]["implemented_rules"] >= 36
    assert any(entry["identifier"] == "10.1" and entry["implemented"] for entry in payload["entries"])


@pytest.mark.asyncio
async def test_rule_implementation_roadmap_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/rules/catalog/roadmap")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] >= 140
    entries_by_id = {entry["identifier"]: entry for entry in payload["entries"]}
    assert entries_by_id["2.1"]["tier"] == "implemented"
    assert entries_by_id["9.1"]["tier"] == "implemented"
    assert "cfg" in entries_by_id["2.1"]["capabilities"]
    tiers = {entry["tier"] for entry in payload["entries"]}
    assert tiers <= {"implemented", "ready_now", "blocked_on_ast_metadata", "blocked_on_process"}
