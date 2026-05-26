from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_all_ok(client: AsyncClient):
    with (
        patch("app.api.health._check_database", new=AsyncMock(return_value={"status": "ok", "latency_ms": 1.0})),
        patch("app.api.health._check_redis",    new=AsyncMock(return_value={"status": "ok", "latency_ms": 0.5})),
        patch("app.api.health._check_groq",     new=AsyncMock(return_value={"status": "ok", "latency_ms": 80.0})),
    ):
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert all(v["status"] == "ok" for v in body["checks"].values())


@pytest.mark.asyncio
async def test_health_db_down(client: AsyncClient):
    with (
        patch("app.api.health._check_database", new=AsyncMock(return_value={"status": "error", "error": "refused"})),
        patch("app.api.health._check_redis",    new=AsyncMock(return_value={"status": "ok", "latency_ms": 0.5})),
        patch("app.api.health._check_groq",     new=AsyncMock(return_value={"status": "ok", "latency_ms": 80.0})),
    ):
        resp = await client.get("/health")

    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"
