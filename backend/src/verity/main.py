"""The FastAPI application factory.

Deliberately mounts no domain routes. Every module registers its own router here as it
lands; until then the only endpoints are the operational probes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from verity import __version__
from verity.core.config import Settings, get_settings
from verity.core.db import dispose_engine
from verity.core.errors import install_exception_handlers
from verity.core.health import router as health_router
from verity.core.logging import configure_logging, get_logger
from verity.core.middleware import (
    AccessLogMiddleware,
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
)
from verity.modules.assets.router import assets_router
from verity.modules.audit.router import router as audit_router
from verity.modules.compliance.control_router import controls_router
from verity.modules.compliance.engagement_router import engagement_router
from verity.modules.compliance.router import frameworks_router, templates_router
from verity.modules.documents.router import documents_router
from verity.modules.evidence.router import evidence_router
from verity.modules.iam.router import (
    auth_router,
    groups_router,
    members_router,
    roles_router,
    security_router,
)
from verity.modules.iam.router import provider_router as iam_provider_router
from verity.modules.notifications.router import notifications_router
from verity.modules.tasks.router import tasks_router
from verity.modules.tenancy.provider_auth import router as provider_auth_router
from verity.modules.tenancy.router import provider_tenants_router, tenant_router
from verity.modules.vendors.portal_router import vendor_portal_router
from verity.modules.vendors.router import vendors_router
from verity.modules.vulnerabilities.router import vulnerabilities_router

logger = get_logger(__name__)

API_PREFIX = "/api/v1"
OPENAPI_URL = f"{API_PREFIX}/openapi.json"
DOCS_URL = f"{API_PREFIX}/docs"
REDOC_URL = f"{API_PREFIX}/redoc"

DESCRIPTION = """
Verity — multi-tenant SOC 2 / GRC compliance platform.

The tenant is never a path or query parameter. It is resolved from the authenticated
session and verified against the caller's membership. Errors return
`{"error": {"code", "message", "correlation_id"}}`; switch on `code`, never on
`message`.
""".strip()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("service.started", env=settings.env, version=__version__)
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("service.stopped")


def _middleware(settings: Settings) -> list[Middleware]:
    """Outermost first.

    The correlation id is assigned before anything else so the access log and the
    exception handlers both have it.
    """
    stack = [
        Middleware(CorrelationIdMiddleware),
        Middleware(AccessLogMiddleware),
        Middleware(
            SecurityHeadersMiddleware,
            csp_exempt_paths=frozenset({DOCS_URL, REDOC_URL}),
        ),
    ]
    if settings.cors_allow_origins:
        stack.append(
            Middleware(
                CORSMiddleware,
                allow_origins=list(settings.cors_allow_origins),
                allow_credentials=True,
                allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
            )
        )
    return stack


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application.

    A factory rather than a module-level singleton so tests can build an app against a
    settings object of their own without reaching into a global.
    """
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Verity API",
        version=__version__,
        description=DESCRIPTION,
        openapi_url=OPENAPI_URL,
        # The interactive docs describe every route including the ones behind auth.
        # They belong on a laptop, not on a deployed host.
        docs_url=DOCS_URL if not settings.is_deployed else None,
        redoc_url=REDOC_URL if not settings.is_deployed else None,
        lifespan=lifespan,
        middleware=_middleware(settings),
    )

    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(audit_router, prefix=API_PREFIX)
    app.include_router(frameworks_router, prefix=API_PREFIX)
    app.include_router(templates_router, prefix=API_PREFIX)
    app.include_router(controls_router, prefix=API_PREFIX)
    app.include_router(engagement_router, prefix=API_PREFIX)
    app.include_router(evidence_router, prefix=API_PREFIX)
    app.include_router(documents_router, prefix=API_PREFIX)
    app.include_router(tasks_router, prefix=API_PREFIX)
    app.include_router(notifications_router, prefix=API_PREFIX)
    app.include_router(assets_router, prefix=API_PREFIX)
    app.include_router(vulnerabilities_router, prefix=API_PREFIX)
    app.include_router(vendors_router, prefix=API_PREFIX)
    # Unauthenticated by design — see modules/vendors/portal_router.py. Mounted
    # under its own path so a proxy can treat it as a distinct surface.
    app.include_router(vendor_portal_router, prefix=API_PREFIX)
    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(members_router, prefix=API_PREFIX)
    app.include_router(groups_router, prefix=API_PREFIX)
    app.include_router(roles_router, prefix=API_PREFIX)
    app.include_router(security_router, prefix=API_PREFIX)
    app.include_router(iam_provider_router, prefix=API_PREFIX)
    app.include_router(provider_auth_router, prefix=API_PREFIX)
    app.include_router(provider_tenants_router, prefix=API_PREFIX)
    app.include_router(tenant_router, prefix=API_PREFIX)
    return app


app = create_app()
