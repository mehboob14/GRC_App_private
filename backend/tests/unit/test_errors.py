"""The error envelope (docs/conventions/api.md)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel
from starlette.middleware import Middleware

from verity.core.errors import (
    INTERNAL_ERROR_CODE,
    Conflict,
    NotFound,
    PermissionDenied,
    VerityError,
    install_exception_handlers,
)
from verity.core.middleware import CORRELATION_ID_HEADER, CorrelationIdMiddleware

LEAKY_DETAIL = 'relation "controls" does not exist at character 15'


class Body(BaseModel):
    count: int


def _build_app() -> FastAPI:
    router = APIRouter()

    @router.get("/not-found")
    async def not_found() -> None:
        raise NotFound(detail="control 0198f0c0 belongs to tenant b")

    @router.get("/forbidden")
    async def forbidden() -> None:
        raise PermissionDenied

    @router.get("/conflict")
    async def conflict() -> None:
        raise Conflict("Evidence has already been approved.")

    @router.get("/boom")
    async def boom() -> None:
        raise RuntimeError(LEAKY_DETAIL)

    @router.get("/http-exception")
    async def http_exception() -> None:
        raise HTTPException(status_code=404, detail=LEAKY_DETAIL)

    @router.post("/validated")
    async def validated(body: Body) -> Body:
        return body

    app = FastAPI(middleware=[Middleware(CorrelationIdMiddleware)])
    install_exception_handlers(app)
    app.include_router(router)
    return app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = _build_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_domain_error_uses_the_one_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/not-found")
    assert response.status_code == 404
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "correlation_id"}
    assert response.json()["error"]["code"] == "not_found"


async def test_declared_status_is_used(client: httpx.AsyncClient) -> None:
    assert (await client.get("/forbidden")).status_code == 403
    assert (await client.get("/conflict")).status_code == 409


async def test_message_can_be_overridden_per_raise(client: httpx.AsyncClient) -> None:
    body = (await client.get("/conflict")).json()
    assert body["error"]["message"] == "Evidence has already been approved."


async def test_internal_detail_never_reaches_the_client(client: httpx.AsyncClient) -> None:
    """The whole point of the ``detail`` argument: it is for the log, not the response."""
    body = (await client.get("/not-found")).text
    assert "0198f0c0" not in body
    assert "tenant b" not in body


async def test_unexpected_exception_returns_a_generic_body(client: httpx.AsyncClient) -> None:
    response = await client.get("/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == INTERNAL_ERROR_CODE
    assert LEAKY_DETAIL not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


async def test_http_exception_detail_is_not_echoed(client: httpx.AsyncClient) -> None:
    """A route that puts an internal reason in ``detail`` must not leak it."""
    response = await client.get("/http-exception")
    assert response.status_code == 404
    assert LEAKY_DETAIL not in response.text
    assert response.json()["error"]["code"] == "not_found"


async def test_validation_failure_is_422_with_a_stable_code(client: httpx.AsyncClient) -> None:
    response = await client.post("/validated", json={"count": "not-a-number"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_redacted_validation_errors_drop_the_submitted_input() -> None:
    """A rejected field's value (a TOTP code, a password) must never be logged."""
    from fastapi.exceptions import RequestValidationError

    from verity.core.errors import _redact_validation_errors

    exc = RequestValidationError(
        [
            {
                "type": "string_type",
                "loc": ("body", "code"),
                "msg": "Input should be a valid string",
                "input": "482913",  # a live TOTP code — must not survive
                "ctx": {"secret": "482913"},
            }
        ]
    )
    redacted = _redact_validation_errors(exc)
    assert redacted == [
        {"type": "string_type", "loc": ("body", "code"), "msg": "Input should be a valid string"}
    ]
    assert "482913" not in str(redacted)


async def test_correlation_id_is_echoed_and_matches_the_body(client: httpx.AsyncClient) -> None:
    response = await client.get("/not-found", headers={CORRELATION_ID_HEADER: "req-abc-123"})
    assert response.headers[CORRELATION_ID_HEADER] == "req-abc-123"
    assert response.json()["error"]["correlation_id"] == "req-abc-123"


async def test_correlation_id_is_generated_when_absent(client: httpx.AsyncClient) -> None:
    response = await client.get("/not-found")
    generated = response.headers[CORRELATION_ID_HEADER]
    assert generated
    assert response.json()["error"]["correlation_id"] == generated


async def test_unsafe_client_correlation_id_is_replaced(client: httpx.AsyncClient) -> None:
    """A client that can inject into a log line can forge log entries."""
    response = await client.get("/not-found", headers={CORRELATION_ID_HEADER: "abc def<script>"})
    assert response.headers[CORRELATION_ID_HEADER] != "abc def<script>"


def test_repr_of_a_domain_error_carries_no_message_or_detail() -> None:
    error = NotFound("Evidence item not found.", detail="tenant a asked for tenant b's row")
    assert repr(error) == "NotFound(code='not_found', http_status=404)"


def test_base_error_defaults_to_a_generic_internal_error() -> None:
    error = VerityError()
    assert error.code == INTERNAL_ERROR_CODE
    assert error.http_status == 500
