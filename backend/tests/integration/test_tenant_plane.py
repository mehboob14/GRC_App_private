"""``GET /api/v1/tenant`` and ``/api/v1/tenant/branding`` through the real app.

``require`` and ``get_tenant_context`` are Week 1 placeholders until IAM lands, so —
exactly as the audit route test does — the authentication *outcomes* are minted
through ``dependency_overrides`` targeting the exact dependency objects the routes
declare. The routes, schemas, service, repository, RLS policies, and error envelope
are all real: the session the overrides yield is genuinely tenant-bound, so the
SELECT-only policies are what answers.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.support.tenancy import register_tenant_directly, seed_admin
from verity.core.config import Settings
from verity.core.db import dispose_engine, get_engine, provider_session_scope, session_scope
from verity.core.deps import TenantContext, get_tenant_context, get_tenant_session
from verity.core.errors import AuthenticationRequired, NotFound
from verity.core.rls import bind_tenant_context
from verity.main import create_app
from verity.modules.tenancy.router import require_tenant_read
from verity.modules.tenancy.schemas import BrandingPut
from verity.modules.tenancy.service import tenancy_service

pytestmark = pytest.mark.integration

TENANT_URL = "/api/v1/tenant"
BRANDING_URL = "/api/v1/tenant/branding"


@pytest.fixture(autouse=True)
async def _clean_state(clean_tenancy: None, clean_audit_log: None) -> AsyncIterator[None]:
    await dispose_engine()
    yield
    await dispose_engine()


@pytest.fixture
async def tenant_id() -> uuid.UUID:
    """A registered tenant with notes and an encrypted SMTP credential on file."""
    admin = await seed_admin()
    tenant = await register_tenant_directly(
        admin.id, "acme", notes="operator-only remark about the customer"
    )
    async with provider_session_scope() as session:
        await tenancy_service.put_branding(
            session,
            actor_admin_id=admin.id,
            tenant_id=tenant.id,
            body=BrandingPut(
                primary_color="#0f172a",
                smtp_config_ref="smtp://mailer:hunter2@smtp.acme.example",
            ),
        )
    return tenant.id


@pytest.fixture
def app(settings: Settings, tenant_id: uuid.UUID) -> FastAPI:
    """The real app with the caller minted as a permitted member of the tenant."""
    application = create_app(settings)
    sessions = async_sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)

    async def permitted() -> None:
        return None

    async def tenant_context() -> TenantContext:
        return TenantContext(tenant_id=tenant_id, membership_id=uuid.uuid4())

    async def tenant_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session, session.begin():
            await bind_tenant_context(session, tenant_id)
            yield session

    application.dependency_overrides[require_tenant_read] = permitted
    application.dependency_overrides[get_tenant_context] = tenant_context
    application.dependency_overrides[get_tenant_session] = tenant_session
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_a_tenant_reads_its_own_profile_without_provider_bookkeeping(
    client: httpx.AsyncClient, tenant_id: uuid.UUID
) -> None:
    response = await client.get(TENANT_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(tenant_id)
    assert body["slug"] == "acme"
    assert body["status"] == "provisioning"
    assert "notes" not in body, "operator notes about the customer are not for the customer"
    assert "created_by" not in body
    assert body["created_at"].endswith("Z")


async def test_a_tenant_reads_its_branding_without_the_smtp_credential(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get(BRANDING_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["primary_color"] == "#0f172a"
    assert "smtp_config_ref" not in body
    assert "hunter2" not in response.text


async def test_the_routes_offer_no_write_methods(client: httpx.AsyncClient) -> None:
    """Lifecycle, plan, and slug cannot be written from the tenant plane: there is
    no verb to try, and the RLS policy behind it is SELECT-only besides."""
    for url in (TENANT_URL, BRANDING_URL):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            response = await client.request(method, url, json={"status": "active"})
            assert response.status_code == 405, f"{method} {url}"


async def test_an_unauthenticated_caller_is_401(app: FastAPI, client: httpx.AsyncClient) -> None:
    async def unauthenticated() -> None:
        raise AuthenticationRequired()

    app.dependency_overrides[require_tenant_read] = unauthenticated
    for url in (TENANT_URL, BRANDING_URL):
        response = await client.get(url)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "authentication_required"


async def test_another_tenants_branding_reads_as_absent_not_forbidden(
    tenant_id: uuid.UUID,
) -> None:
    """From a session bound to tenant A, tenant B's branding row is not a thing that
    exists — the service raises NotFound (the API's 404), never a permission error."""
    admin = await seed_admin(email="second@example.com")
    other = await register_tenant_directly(admin.id, "rival")
    async with session_scope(tenant_id) as session:
        with pytest.raises(NotFound):
            await tenancy_service.get_own_branding(session, other.id)
