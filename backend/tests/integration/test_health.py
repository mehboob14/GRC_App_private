"""Liveness and readiness against the real stack."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from verity.core.config import Settings
from verity.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_liveness_answers_without_touching_a_dependency(
    client: httpx.AsyncClient,
) -> None:
    """No dependency call, so a database outage does not get every replica restarted."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_liveness_carries_the_security_headers(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-correlation-id"]


async def test_readiness_reports_each_dependency(
    client: httpx.AsyncClient,
    app_engine: object,
) -> None:
    response = await client.get("/readyz")
    body = response.json()
    assert set(body["dependencies"]) == {"database", "redis"}
    if response.status_code == 200:
        assert body["status"] == "ready"
        assert set(body["dependencies"].values()) == {"ok"}
    else:
        assert response.status_code == 503
        assert body["status"] == "not_ready"


async def test_readiness_leaks_no_connection_detail(client: httpx.AsyncClient) -> None:
    """An unauthenticated probe that echoes a driver error is a map of the network."""
    body = (await client.get("/readyz")).text
    for leak in ("postgresql", "asyncpg", "localhost", "5432", "password", "redis://"):
        assert leak not in body.lower()


async def test_openapi_is_served_and_describes_the_probes(client: httpx.AsyncClient) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()
    assert schema["info"]["title"] == "Verity API"
    assert "/healthz" in schema["paths"]
    assert "/readyz" in schema["paths"]


async def test_an_unknown_route_uses_the_error_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/no-such-route")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
