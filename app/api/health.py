import asyncio
import time
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette import status

from app.core.config import settings
from app.core.database import async_session_factory

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["monitoring"])


async def _check_database() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": _ms(t0)}
    except Exception as exc:
        logger.error("health_db_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


async def _check_redis() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        return {"status": "ok", "latency_ms": _ms(t0)}
    except Exception as exc:
        logger.error("health_redis_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


async def _check_groq() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            )
            resp.raise_for_status()
        return {"status": "ok", "latency_ms": _ms(t0)}
    except Exception as exc:
        logger.error("health_groq_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


@router.get("/health")
async def health_check() -> JSONResponse:
    db_r, redis_r, groq_r = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_groq(),
    )

    checks = {"database": db_r, "redis": redis_r, "groq": groq_r}
    all_ok = all(v["status"] == "ok" for v in checks.values())

    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        content={
            "status": "healthy" if all_ok else "degraded",
            "checks": checks,
            "timestamp": time.time(),
        },
        status_code=http_status,
    )
