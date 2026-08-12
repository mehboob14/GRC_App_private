"""Liveness and readiness.

They are separate on purpose. ``/healthz`` says the process is alive and contacts
nothing, so a database outage does not get every replica killed and restarted into the
same outage. ``/readyz`` says the dependencies answer, so an unready replica is taken
out of the load balancer and left running.

Neither reports a host, a DSN, a credential, or a driver message. An unauthenticated
probe endpoint that echoes a connection error is a free map of the internal network.
"""

from __future__ import annotations

import asyncio
from typing import Final, Literal

import redis.asyncio as aioredis
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from verity import __version__
from verity.core.config import Settings, get_settings
from verity.core.db import get_engine
from verity.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["operations"])

DependencyStatus = Literal["ok", "unavailable"]

_PROBE_TIMEOUT_SECONDS: Final = 5.0


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, DependencyStatus]


async def _check_database() -> DependencyStatus:
    try:
        async with (
            asyncio.timeout(_PROBE_TIMEOUT_SECONDS),
            get_engine().connect() as connection,
        ):
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.warning("readiness.database_unavailable", exc_info=True)
        return "unavailable"
    else:
        return "ok"


async def _check_redis(settings: Settings) -> DependencyStatus:
    client = aioredis.from_url(
        settings.redis.url,
        socket_timeout=settings.redis.socket_timeout_seconds,
        socket_connect_timeout=settings.redis.socket_timeout_seconds,
    )
    try:
        async with asyncio.timeout(_PROBE_TIMEOUT_SECONDS):
            await client.ping()
    except Exception:
        logger.warning("readiness.redis_unavailable", exc_info=True)
        return "unavailable"
    else:
        return "ok"
    finally:
        await client.aclose()


@router.get(
    "/healthz",
    response_model=LivenessResponse,
    summary="Liveness — the process is running",
)
async def healthz() -> LivenessResponse:
    settings = get_settings()
    return LivenessResponse(status="ok", service=settings.service_name, version=__version__)


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    summary="Readiness — the dependencies answer",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readyz(response: Response) -> ReadinessResponse:
    settings = get_settings()
    database, cache = await asyncio.gather(_check_database(), _check_redis(settings))
    dependencies: dict[str, DependencyStatus] = {"database": database, "redis": cache}
    ready = all(state == "ok" for state in dependencies.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ready" if ready else "not_ready", dependencies=dependencies)
