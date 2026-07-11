import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "misra_http_requests_total" in response.text
