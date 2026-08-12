"""Security headers (docs/security/baseline.md)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from starlette.middleware import Middleware

from verity.core.middleware import (
    API_CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
)

DOCS_PATH = "/api/v1/docs"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = FastAPI(
        middleware=[
            Middleware(CorrelationIdMiddleware),
            Middleware(SecurityHeadersMiddleware, csp_exempt_paths=frozenset({DOCS_PATH})),
        ]
    )

    @app.get("/anything")
    async def anything() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get(DOCS_PATH)
    async def docs() -> dict[str, str]:
        return {"ok": "docs"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_every_mandated_header_is_present(client: httpx.AsyncClient) -> None:
    response = await client.get("/anything")
    for name, value in SECURITY_HEADERS:
        assert response.headers[name] == value


async def test_api_responses_carry_a_policy_that_permits_nothing(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/anything")
    assert response.headers["content-security-policy"] == API_CONTENT_SECURITY_POLICY
    assert "unsafe-inline" not in response.headers["content-security-policy"]


async def test_the_docs_page_is_exempt_from_the_api_policy(client: httpx.AsyncClient) -> None:
    """``default-src 'none'`` would blank the page. Docs never ship deployed."""
    response = await client.get(DOCS_PATH)
    assert "content-security-policy" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
