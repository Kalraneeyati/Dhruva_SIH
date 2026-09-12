"""Liveness and readiness.

/health answers whether the process is up. /health/ready answers whether it can
actually do work, and returns 503 when it cannot — a readiness probe that always
returns 200 is a readiness probe that never tells you anything.
"""

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, Response

from dhruva.config import settings

router = APIRouter(tags=["health"])

# The plan puts geofencing, advisory RAG and vessel tracks in one engine.
# If any of these is missing the engine cannot do the job it was chosen for.
REQUIRED_EXTENSIONS = ("postgis", "vector", "timescaledb")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "env": settings.env}


@router.get("/health/ready")
async def ready(response: Response) -> dict[str, object]:
    checks: dict[str, object] = {}
    ok = True

    try:
        conn = await asyncpg.connect(settings.database_url, timeout=5)
        try:
            await conn.fetchval("SELECT 1")
            installed = {r["extname"] for r in await conn.fetch("SELECT extname FROM pg_extension")}
            missing = [e for e in REQUIRED_EXTENSIONS if e not in installed]
            checks["postgres"] = {
                "ok": not missing,
                "extensions": sorted(installed & set(REQUIRED_EXTENSIONS)),
                "missing": missing,
            }
            ok = ok and not missing
        finally:
            await conn.close()
    except Exception as exc:
        checks["postgres"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        ok = False

    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=5)
        try:
            await r.ping()
            checks["redis"] = {"ok": True}
        finally:
            await r.aclose()
    except Exception as exc:
        checks["redis"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        ok = False

    if not ok:
        response.status_code = 503
    return {"ready": ok, "checks": checks}
