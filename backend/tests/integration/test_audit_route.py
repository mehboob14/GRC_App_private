"""``GET /api/v1/audit-log`` through the real app, real database, real policies.

``core.deps.require`` and ``get_tenant_context`` are Week 1 placeholders until the
IAM change lands, so the authentication *outcomes* are minted through FastAPI's
``dependency_overrides`` — the route, the schema, the service, the repository, RLS,
and the error envelope are all real. The overrides target the exact dependency
objects the route declares, so nothing here changes when IAM replaces the bodies.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from verity.core.config import Settings
from verity.core.deps import TenantContext, get_tenant_context, get_tenant_session
from verity.core.errors import AuthenticationRequired, PermissionDenied
from verity.core.rls import bind_tenant_context
from verity.main import create_app
from verity.modules.audit.router import require_audit_read
from verity.modules.audit.service import Membership, audit_service
from verity.shared.ids import uuid7

pytestmark = pytest.mark.integration

TENANT_A = uuid.UUID("0198f0c0-0000-7000-8000-0000000000ad")
TENANT_B = uuid.UUID("0198f0c0-0000-7000-8000-0000000000bd")
MEMBERSHIP_A = uuid.UUID("0198f0c0-0000-7000-8000-0000000000ed")

AUDIT_LOG_URL = "/api/v1/audit-log"


@pytest.fixture
def sessions(
    app_engine: AsyncEngine,
    clean_audit_log: None,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=app_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def seeded_streams(sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    """Three committed rows for tenant A — separate transactions, so ``occurred_at``
    differs and the newest-first order is observable — plus one for tenant B that
    must never appear."""
    object_types = ["control", "risk", "document"]
    for object_type in object_types:
        async with sessions() as session, session.begin():
            await bind_tenant_context(session, TENANT_A)
            await audit_service.record(
                session,
                action="create",
                object_type=object_type,
                object_id=uuid7(),
                actor=Membership(MEMBERSHIP_A),
                tenant_id=TENANT_A,
                after={"seeded": True},
            )
    async with sessions() as session, session.begin():
        await bind_tenant_context(session, TENANT_B)
        await audit_service.record(
            session,
            action="create",
            object_type="secret_of_b",
            object_id=uuid7(),
            actor=Membership(uuid7()),
            tenant_id=TENANT_B,
            after={"seeded": True},
        )
    return object_types


@pytest.fixture
def app(settings: Settings, sessions: async_sessionmaker[AsyncSession]) -> FastAPI:
    """The real app with the caller minted as a permitted member of tenant A."""
    application = create_app(settings)

    async def permitted() -> None:
        return None

    async def tenant_context() -> TenantContext:
        return TenantContext(tenant_id=TENANT_A, membership_id=MEMBERSHIP_A)

    async def tenant_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session, session.begin():
            await bind_tenant_context(session, TENANT_A)
            yield session

    application.dependency_overrides[require_audit_read] = permitted
    application.dependency_overrides[get_tenant_context] = tenant_context
    application.dependency_overrides[get_tenant_session] = tenant_session
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_a_permitted_caller_gets_the_tenants_trail_newest_first(
    client: httpx.AsyncClient,
    seeded_streams: list[str],
) -> None:
    response = await client.get(AUDIT_LOG_URL)
    assert response.status_code == 200
    body = response.json()
    assert [item["object_type"] for item in body["items"]] == list(reversed(seeded_streams))
    assert body["next_cursor"] is None
    for item in body["items"]:
        assert item["tenant_id"] == str(TENANT_A)
        assert item["occurred_at"].endswith("Z"), "ISO 8601 UTC with a Z suffix"
        # The UI renders these; every row must carry non-empty labels (the audit-log
        # page white-screened without them). object_label is humanised kind + short id.
        assert item["actor_label"]
        assert " · " in item["object_label"]
        assert item["object_label"].lower().startswith(item["object_type"].replace("_", " ")[:5])


async def test_the_cursor_walks_the_whole_trail_without_repeats(
    client: httpx.AsyncClient,
    seeded_streams: list[str],
) -> None:
    first = (await client.get(AUDIT_LOG_URL, params={"limit": 2})).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None

    second = (
        await client.get(AUDIT_LOG_URL, params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None

    ids = [item["id"] for item in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 3


async def test_a_client_supplied_tenant_parameter_changes_nothing(
    client: httpx.AsyncClient,
    seeded_streams: list[str],
) -> None:
    """The tenant comes from the session; an uninvited ``tenant_id`` is not part of
    the route's schema and cannot widen the response to tenant B's stream."""
    response = await client.get(AUDIT_LOG_URL, params={"tenant_id": str(TENANT_B)})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert all(item["tenant_id"] == str(TENANT_A) for item in body["items"])
    assert not any(item["object_type"] == "secret_of_b" for item in body["items"])


async def test_a_malformed_cursor_is_a_422_with_a_stable_code(
    client: httpx.AsyncClient,
    seeded_streams: list[str],
) -> None:
    response = await client.get(AUDIT_LOG_URL, params={"cursor": "not-a-cursor"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_input"
    assert error["correlation_id"]


async def test_a_limit_beyond_the_maximum_is_refused(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(AUDIT_LOG_URL, params={"limit": 1000})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_a_caller_without_the_permission_gets_403(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    async def denied() -> None:
        raise PermissionDenied(detail="audit:read not granted")

    app.dependency_overrides[require_audit_read] = denied
    response = await client.get(AUDIT_LOG_URL)
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "permission_denied"
    assert error["correlation_id"]
    assert "audit:read" not in response.text, "internal detail must stay in the log"


async def test_an_unauthenticated_caller_gets_401(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    async def unauthenticated() -> None:
        raise AuthenticationRequired()

    app.dependency_overrides[require_audit_read] = unauthenticated
    response = await client.get(AUDIT_LOG_URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
