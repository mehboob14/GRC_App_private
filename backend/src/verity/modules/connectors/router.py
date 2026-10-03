"""HTTP for connections, runs, the control Automation panel and integration requests.

Reading connections needs ``connectors:read``; connecting, running and
disconnecting need ``connectors:manage``. The Automation panel is part of the
control, so it needs what reading a control needs (``frameworks:read``). Asking
for a new integration is work on a control, so it needs ``controls:manage``.

A manual run is accepted, then collected in the background after the response,
because a large organisation can take minutes to read. The page polls the
connection until the run finishes.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.deps import TenantContext, get_tenant_context, get_tenant_session, require
from verity.modules.audit.service import Membership
from verity.modules.connectors.schemas import (
    AutomationOut,
    ConnectionOut,
    ConnectWrite,
    ControlCompositionOut,
    DisconnectWrite,
    IntegrationRequestOut,
    IntegrationRequestWrite,
    ProviderOut,
    ResourceOut,
    ScopeWrite,
)
from verity.modules.connectors.service import connector_service

connectors_router = APIRouter(tags=["connectors"])

_Ctx = Annotated[TenantContext, Depends(get_tenant_context)]
_Db = Annotated[AsyncSession, Depends(get_tenant_session)]


def _actor(context: TenantContext) -> Membership:
    assert context.membership_id is not None  # noqa: S101
    return Membership(context.membership_id)


@connectors_router.get(
    "/connectors/providers",
    response_model=list[ProviderOut],
    dependencies=[Depends(require("connectors:read"))],
    summary="Every provider in the catalogue, with its status and phase",
)
async def list_providers(session: _Db) -> list[ProviderOut]:
    return [ProviderOut.model_validate(view) for view in await connector_service.providers(session)]


@connectors_router.get(
    "/connections",
    response_model=list[ConnectionOut],
    dependencies=[Depends(require("connectors:read"))],
    summary="This workspace's connections and their health",
)
async def list_connections(context: _Ctx, session: _Db) -> list[ConnectionOut]:
    views = await connector_service.list_connections(session, tenant_id=context.tenant_id)
    return [ConnectionOut.model_validate(view) for view in views]


@connectors_router.post(
    "/connections",
    response_model=ConnectionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require("connectors:manage"))],
    summary="Connect a provider account with a read only token",
)
async def connect(body: ConnectWrite, context: _Ctx, session: _Db) -> ConnectionOut:
    # The page starts the first run with a second call once this one has
    # committed: a background task here could start before the new row is visible.
    view = await connector_service.connect(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        provider=body.provider,
        token=body.token.get_secret_value(),
        account=body.account,
    )
    return ConnectionOut.model_validate(view)


@connectors_router.post(
    "/connections/{connection_id}/disconnect",
    response_model=ConnectionOut,
    dependencies=[Depends(require("connectors:manage"))],
    summary="Destroy the stored token and stop running checks",
)
async def disconnect(
    connection_id: uuid.UUID, body: DisconnectWrite, context: _Ctx, session: _Db
) -> ConnectionOut:
    view = await connector_service.disconnect(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        connection_id=connection_id,
        reason=body.reason,
    )
    return ConnectionOut.model_validate(view)


@connectors_router.get(
    "/connections/{connection_id}/resources",
    response_model=list[ResourceOut],
    dependencies=[Depends(require("connectors:read"))],
    summary="Every repository this connection can see, and whether it is checked",
)
async def list_resources(
    connection_id: uuid.UUID, context: _Ctx, session: _Db
) -> list[ResourceOut]:
    views = await connector_service.resources(
        session, tenant_id=context.tenant_id, connection_id=connection_id
    )
    return [ResourceOut.model_validate(view) for view in views]


@connectors_router.put(
    "/connections/{connection_id}/scope",
    response_model=list[ResourceOut],
    dependencies=[Depends(require("connectors:manage"))],
    summary="Choose which repositories the checks look at",
)
async def set_scope(
    connection_id: uuid.UUID, body: ScopeWrite, context: _Ctx, session: _Db
) -> list[ResourceOut]:
    views = await connector_service.set_scope(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        connection_id=connection_id,
        decisions=[(d.external_id, d.scope) for d in body.decisions],
        reason=body.reason,
    )
    return [ResourceOut.model_validate(view) for view in views]


@connectors_router.post(
    "/connections/{connection_id}/runs",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require("connectors:manage"))],
    summary="Run this connection's checks now",
)
async def run_now(
    connection_id: uuid.UUID, context: _Ctx, session: _Db, background: BackgroundTasks
) -> dict[str, bool]:
    await connector_service.ensure_runnable(
        session, tenant_id=context.tenant_id, connection_id=connection_id
    )
    background.add_task(
        connector_service.run,
        tenant_id=context.tenant_id,
        connection_id=connection_id,
        trigger="manual",
        actor=_actor(context),
    )
    return {"accepted": True}


@connectors_router.get(
    "/controls/{control_id}/automation",
    response_model=AutomationOut,
    dependencies=[Depends(require("frameworks:read"))],
    summary="Tests, providers and live results for one control",
)
async def control_automation(control_id: uuid.UUID, context: _Ctx, session: _Db) -> AutomationOut:
    view = await connector_service.control_automation(
        session, tenant_id=context.tenant_id, control_id=control_id
    )
    return AutomationOut.model_validate(view)


@connectors_router.get(
    "/control-composition",
    response_model=list[ControlCompositionOut],
    dependencies=[Depends(require("frameworks:read"))],
    summary="What evidences each control: systems, Verity modules and people",
)
async def control_composition(context: _Ctx, session: _Db) -> list[ControlCompositionOut]:
    views = await connector_service.compositions(session, tenant_id=context.tenant_id)
    return [ControlCompositionOut.model_validate(view) for view in views]


@connectors_router.get(
    "/integration-requests",
    response_model=list[IntegrationRequestOut],
    dependencies=[Depends(require("connectors:read"))],
    summary="Systems this workspace has asked Verity to support",
)
async def list_requests(context: _Ctx, session: _Db) -> list[IntegrationRequestOut]:
    views = await connector_service.list_requests(session, tenant_id=context.tenant_id)
    return [IntegrationRequestOut.model_validate(view) for view in views]


@connectors_router.post(
    "/integration-requests",
    response_model=IntegrationRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require("controls:manage"))],
    summary="Ask Verity to support a system it cannot connect to yet",
)
async def request_integration(
    body: IntegrationRequestWrite, context: _Ctx, session: _Db
) -> IntegrationRequestOut:
    view = await connector_service.request_integration(
        session,
        tenant_id=context.tenant_id,
        actor=_actor(context),
        provider_name=body.provider_name,
        capability_key=body.capability_key,
        control_id=body.control_id,
        note=body.note,
    )
    return IntegrationRequestOut.model_validate(view)
