"""Documents through the real app: teammates who hold the keys a test needs, the
approval flow that publishes, campaigns, and a way to move the clock.

Nothing here writes a table directly except ``backdate``. The clock cannot be moved, and
a review date or a reminder cannot be made to lapse without waiting, so that one helper
rewrites a timestamp as the application role inside the tenant's own transaction. Row-level
security still applies to it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import text

from tests.support.iam import (
    INVITEE_PASSWORD,
    Workspace,
    invite_directly,
    tenant_session_headers,
)
from verity.core.db import session_scope
from verity.modules.iam.service import iam_auth_service

READER = ("tenant:read", "documents:read")
MANAGER = (*READER, "documents:manage")


@dataclass(frozen=True, slots=True)
class Teammate:
    membership_id: uuid.UUID
    email: str
    name: str

    @property
    def headers(self) -> dict[str, str]:
        return tenant_session_headers(self.membership_id)


def client(app: FastAPI, headers: dict[str, str]) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1", headers=headers
    )


def today() -> date:
    return datetime.now(UTC).date()


def at(day: date) -> str:
    """A due date the way the campaign dialog sends one: midnight UTC."""
    return f"{day.isoformat()}T00:00:00Z"


async def add_teammate(  # noqa: PLR0913 — who they are and what they may do
    app: FastAPI,
    admin: httpx.AsyncClient,
    workspace: Workspace,
    *,
    email: str,
    name: str,
    keys: tuple[str, ...] = READER,
) -> Teammate:
    """An active member whose only keys are ``keys``."""
    invited = await invite_directly(
        workspace, email=email, full_name=name, role_name="Chief Executive Officer"
    )
    await iam_auth_service.accept_invitation(
        token=invited.invite_token, full_name=name, password=INVITEE_PASSWORD
    )
    role = await admin.post(
        "/roles", json={"name": f"Documents for {name}", "permission_keys": list(keys)}
    )
    assert role.status_code == 201, role.text
    assignment = await admin.post(
        f"/roles/{role.json()['id']}/assignments",
        json={"assignee_type": "membership", "assignee_id": str(invited.member.membership_id)},
    )
    assert assignment.status_code == 201, assignment.text
    return Teammate(membership_id=invited.member.membership_id, email=email, name=name)


async def create_document(
    admin: httpx.AsyncClient, workspace: Workspace, **fields: object
) -> dict[str, Any]:
    """A draft the workspace's admin owns (an owner is what lets it be sent for approval)."""
    body = {
        "title": "Acceptable Use Policy",
        "doc_type": "policy",
        "owner_membership_id": str(workspace.membership_id),
        **fields,
    }
    response = await admin.post("/documents", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def publish(
    admin: httpx.AsyncClient, document_id: str, approver: uuid.UUID
) -> dict[str, Any]:
    """Run both approval tiers to the end. The last approval publishes by itself."""
    for tier in (1, 2):
        assigned = await admin.post(
            f"/documents/{document_id}/approvals/{tier}/assign",
            json={"targets": {"user_ids": [str(approver)]}},
        )
        assert assigned.status_code == 200, assigned.text
    for tier in (1, 2):
        decided = await admin.post(
            f"/documents/{document_id}/approvals/{tier}/decide", json={"decision": "approved"}
        )
        assert decided.status_code == 200, decided.text
    detail = await admin.get(f"/documents/{document_id}")
    assert detail.status_code == 200, detail.text
    body: dict[str, Any] = detail.json()
    assert body["lifecycle"] == "published", body["lifecycle"]
    return body


async def start_campaign(
    admin: httpx.AsyncClient,
    document_id: str,
    *people: Teammate | uuid.UUID,
    title: str = "Annual acknowledgement",
    due: date | None = None,
    approvers: tuple[Teammate | uuid.UUID, ...] = (),
) -> dict[str, Any]:
    def ids(group: tuple[Teammate | uuid.UUID, ...]) -> list[str]:
        return [str(p.membership_id if isinstance(p, Teammate) else p) for p in group]

    response = await admin.post(
        f"/documents/{document_id}/campaigns",
        json={
            "title": title,
            "reviewers": {"user_ids": ids(people)},
            "approvers": {"user_ids": ids(approvers)},
            "due_at": at(due) if due else None,
        },
    )
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def sign(
    app: FastAPI, who: Teammate, campaign_id: str, comment: str | None = None
) -> dict[str, Any]:
    async with client(app, who.headers) as api:
        response = await api.post(
            f"/documents/campaigns/{campaign_id}/acknowledge", json={"comment": comment}
        )
    assert response.status_code == 200, response.text
    signed: dict[str, Any] = response.json()
    return signed


async def inbox(app: FastAPI, headers: dict[str, str], kind: str | None = None) -> list[Any]:
    async with client(app, headers) as api:
        response = await api.get("/notifications", params={"limit": 100})
    assert response.status_code == 200, response.text
    items: list[Any] = response.json()["items"]
    return [n for n in items if kind is None or n["kind"] == kind]


async def backdate(workspace: Workspace, statement: str, **params: object) -> None:
    """Run one UPDATE that moves a timestamp or date into the past, inside the tenant."""
    async with session_scope(workspace.tenant_id) as session:
        await session.execute(text(statement), params)
