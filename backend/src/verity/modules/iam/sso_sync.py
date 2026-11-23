"""Keeping a workspace's members in step with its Keycloak organization (add-keycloak-sso phase D).

ADR-0015 decision 4: lifecycle comes from Keycloak, whatever feeds Keycloak (brokered sign in, SCIM,
LDAP). The sync reads the organization's members and their organization groups through the Admin
API, outside any transaction, then applies them in the workspace's own transaction. It governs only
members linked to Keycloak whose email is in a domain the workspace proved:

- one who left the organization, or is disabled there, loses the membership (disabled with a
  reason, never deleted), and with it every session;
- each holds the roles the group map gives them; the sync takes back only roles it granted
  (``source = 'sso_group'``), never one an admin gave;
- with provisioning on, an organization member with a verified email in a proven domain and no
  membership yet becomes a member with the default role.

The workspace's last active Admin is never disabled nor stripped of Admin. Fail closed: when
Keycloak cannot be read, or the organization comes back empty while governed members exist,
nothing changes. Every change is audited.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from verity.core.config import get_settings
from verity.core.db import provider_session_scope, session_scope
from verity.core.errors import Conflict, InvalidInput, NotFound, UpstreamUnavailable
from verity.core.logging import get_logger
from verity.modules.audit.service import Actor, AuditService, Membership, System, audit_service
from verity.modules.iam.keycloak_admin import KeycloakAdmin
from verity.modules.iam.models import (
    ADMIN_ROLE_NAME,
    ASSIGNEE_TYPE_MEMBERSHIP,
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_DISABLED,
    RoleAssignment,
    SsoGroupRole,
    TenantMembership,
)
from verity.modules.iam.repository import (
    IdentityRepository,
    MembershipRepository,
    RoleRepository,
    SsoRepository,
    UserRepository,
)
from verity.modules.iam.service import iam_auth_service
from verity.shared.ids import uuid7

logger = get_logger(__name__)

SOURCE: Final = "sso_group"
_MEMBERSHIP: Final = ("id", "tenant_id", "user_id", "status", "disabled_at")
_ASSIGNMENT: Final = ("id", "tenant_id", "role_id", "assignee_type", "assignee_id", "source")


@dataclass(slots=True)
class SyncResult:
    skipped: str | None = None
    created: int = 0
    disabled: int = 0
    granted: int = 0
    revoked: int = 0
    kept: int = 0
    """Changes left undone so the workspace keeps an active Admin."""


class SsoSyncService:
    def __init__(self, admin: KeycloakAdmin | None = None) -> None:
        self._admin = admin
        self._audit = audit_service
        self._sso = SsoRepository()
        self._memberships = MembershipRepository()
        self._users = UserRepository()
        self._identities = IdentityRepository()
        self._roles = RoleRepository()

    def _keycloak(self) -> KeycloakAdmin:
        return self._admin or KeycloakAdmin()

    # -- the group to role map ------------------------------------------------------------

    async def add_group_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        group_name: str,
        role_id: uuid.UUID,
    ) -> None:
        name = group_name.strip()
        if not 1 <= len(name) <= 255:  # noqa: PLR2004 — the column's check
            raise InvalidInput("Type the group's name as Keycloak shows it.", detail="group name")
        if await self._roles.get_for_tenant(session, tenant_id, role_id) is None:
            raise NotFound("That role no longer exists.", detail=f"role {role_id}")
        existing = await self._sso.group_roles(session, tenant_id)
        if any(m.group_name == name and m.role_id == role_id for m in existing):
            raise Conflict("That group already gives that role.", detail=f"{name} {role_id}")
        row = SsoGroupRole(id=uuid7(), tenant_id=tenant_id, group_name=name, role_id=role_id)
        await self._sso.add_group_role(session, row)
        await self._audit.record(
            session,
            action="create",
            object_type="sso_group_role",
            object_id=row.id,
            actor=Membership(actor_membership_id),
            tenant_id=tenant_id,
            after={"group_name": name, "role_id": str(role_id)},
        )

    async def remove_group_role(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        actor_membership_id: uuid.UUID,
        mapping_id: uuid.UUID,
    ) -> None:
        """The next sync takes back the roles this mapping gave."""
        row = await self._sso.get_group_role(session, tenant_id, mapping_id)
        if row is None:
            raise NotFound("That group mapping no longer exists.", detail=f"mapping {mapping_id}")
        await self._audit.record(
            session,
            action="delete",
            object_type="sso_group_role",
            object_id=row.id,
            actor=Membership(actor_membership_id),
            tenant_id=tenant_id,
            before={"group_name": row.group_name, "role_id": str(row.role_id)},
        )
        await self._sso.delete_group_role(session, row)

    # -- the sync -------------------------------------------------------------------------

    async def sync_all(self) -> dict[str, int]:
        """Every workspace with SSO on; one workspace's failure never stops the others."""
        async with provider_session_scope() as plane:
            tenant_ids = await self._sso.enabled_tenant_ids(plane)
        synced = failed = 0
        for tenant_id in tenant_ids:
            try:
                await self.sync_tenant(tenant_id)
                synced += 1
            except Exception:
                logger.exception("sso.sync_failed", tenant_id=str(tenant_id))
                failed += 1
        return {"synced": synced, "failed": failed}

    async def sync_tenant(
        self, tenant_id: uuid.UUID, *, actor_membership_id: uuid.UUID | None = None
    ) -> SyncResult:
        """One workspace. ``actor_membership_id`` is the admin who pressed Sync now; the
        scheduled run acts as the system."""
        actor: Actor = Membership(actor_membership_id) if actor_membership_id else System()
        async with session_scope(tenant_id) as session:
            row = await self._sso.get(session, tenant_id)
            alias = row.organization_alias if row is not None and row.enabled else None
        if alias is None:
            return SyncResult(skipped="off")
        keycloak = self._keycloak()
        org = await keycloak.organization(alias)
        if org is None:
            raise UpstreamUnavailable(
                "Keycloak has no organization with this workspace's alias.",
                detail=f"organization {alias} not found",
            )
        # ponytail: one groups call per member; list each group's members if organizations
        # grow to thousands of people.
        members = await keycloak.members(org["id"])
        groups = {
            m["id"]: await keycloak.member_groups(org["id"], m["id"])
            for m in members
            if m.get("enabled", True)
        }
        async with session_scope(tenant_id) as session:
            return await self._apply(session, tenant_id, members, groups, actor)

    async def _apply(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        members: list[dict[str, Any]],
        groups: dict[str, list[str]],
        actor: Actor,
    ) -> SyncResult:
        result = SyncResult()
        row = await self._sso.get(session, tenant_id)
        if row is None or not row.enabled:
            return SyncResult(skipped="off")
        maps = await self._sso.group_roles(session, tenant_id)
        memberships = await self._memberships.list_for_tenant(session, tenant_id)
        users = {
            u.id: u for u in await self._users.get_many(session, [m.user_id for m in memberships])
        }
        subjects = await self._identities.subjects_for(
            session, provider=get_settings().oidc.provider_key, user_ids=list(users)
        )

        def proven(email: str | None) -> bool:
            return (email or "").lower().rpartition("@")[2] in row.verified_domains

        def wanted(member_id: str) -> set[uuid.UUID]:
            names = set(groups.get(member_id, []))
            return {m.role_id for m in maps if m.group_name in names}

        governed = [
            m for m in memberships if m.user_id in subjects and proven(users[m.user_id].email)
        ]
        if not members and any(m.status == MEMBERSHIP_STATUS_ACTIVE for m in governed):
            logger.warning("sso.sync_empty_organization", tenant_id=str(tenant_id))
            return SyncResult(skipped="empty")
        by_id = {m["id"]: m for m in members}
        for membership in governed:
            if membership.status != MEMBERSHIP_STATUS_ACTIVE:
                continue
            member = by_id.get(subjects[membership.user_id])
            if member is None or not member.get("enabled", True):
                await self._disable(session, membership, actor, result, gone=member is None)
            else:
                await self._reconcile(session, membership, wanted(member["id"]), actor, result)

        if row.jit_enabled and row.default_role_id is not None:
            known = set(subjects.values())
            for member in members:
                email = member.get("email")
                if (
                    member["id"] in known
                    or not member.get("enabled", True)
                    or not member.get("emailVerified")
                    or not proven(email)
                ):
                    continue
                name = " ".join(p for p in (member.get("firstName"), member.get("lastName")) if p)
                made = await iam_auth_service.provision_sso_member(
                    session,
                    tenant_id=tenant_id,
                    email=str(email),
                    full_name=name,
                    subject=member["id"],
                    role_id=row.default_role_id,
                    actor=actor,
                )
                if made is not None:
                    result.created += 1
                    await self._reconcile(session, made, wanted(member["id"]), actor, result)
        row.synced_at = datetime.now(UTC)
        await session.flush([row])
        logger.info("sso.synced", tenant_id=str(tenant_id), result=str(result))
        return result

    async def _reconcile(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        wanted: set[uuid.UUID],
        actor: Actor,
        result: SyncResult,
    ) -> None:
        tenant_id = membership.tenant_id
        direct = await self._roles.list_direct_for_membership(session, tenant_id, membership.id)
        held = {a.role_id for a in direct if a.engagement_id is None}
        for role_id in sorted(wanted - held):
            assignment = RoleAssignment(
                id=uuid7(),
                tenant_id=tenant_id,
                role_id=role_id,
                assignee_type=ASSIGNEE_TYPE_MEMBERSHIP,
                assignee_id=membership.id,
                source=SOURCE,
            )
            await self._roles.add_assignment(session, assignment)
            await self._record(session, actor, "create", assignment, None)
            result.granted += 1
        for assignment in direct:
            if assignment.source != SOURCE or assignment.role_id in wanted:
                continue
            if await self._leaves_no_admin(session, membership, {assignment.role_id}):
                result.kept += 1
                continue
            await self._record(session, actor, "delete", assignment, assignment)
            await self._roles.delete_assignment(session, assignment)
            result.revoked += 1

    async def _disable(
        self,
        session: AsyncSession,
        membership: TenantMembership,
        actor: Actor,
        result: SyncResult,
        *,
        gone: bool,
    ) -> None:
        direct = await self._roles.list_direct_for_membership(
            session, membership.tenant_id, membership.id
        )
        if await self._leaves_no_admin(session, membership, {a.role_id for a in direct}):
            logger.warning("sso.sync_kept_last_admin", membership_id=str(membership.id))
            result.kept += 1
            return
        before = AuditService.snapshot(membership, fields=_MEMBERSHIP)
        membership.status = MEMBERSHIP_STATUS_DISABLED
        membership.disabled_at = datetime.now(UTC)
        await session.flush([membership])
        await self._audit.record(
            session,
            action="update",
            object_type="tenant_membership",
            object_id=membership.id,
            actor=actor,
            tenant_id=membership.tenant_id,
            before=before,
            after={
                **AuditService.snapshot(membership, fields=_MEMBERSHIP),
                "reason": "left the organization in Keycloak" if gone else "disabled in Keycloak",
            },
        )
        result.disabled += 1

    async def _leaves_no_admin(
        self, session: AsyncSession, membership: TenantMembership, role_ids: set[uuid.UUID]
    ) -> bool:
        """Whether taking these roles from this member would leave no active Admin."""
        roles = await self._roles.get_many(session, membership.tenant_id, list(role_ids))
        if not any(r.built_in and r.name == ADMIN_ROLE_NAME for r in roles):
            return False
        return not await self._roles.admin_membership_exists(
            session,
            membership.tenant_id,
            require_active=True,
            excluding_membership_id=membership.id,
        )

    async def _record(
        self,
        session: AsyncSession,
        actor: Actor,
        action: Literal["create", "delete"],
        assignment: RoleAssignment,
        before: RoleAssignment | None,
    ) -> None:
        snap = AuditService.snapshot(assignment, fields=_ASSIGNMENT)
        await self._audit.record(
            session,
            action=action,
            object_type="role_assignment",
            object_id=assignment.id,
            actor=actor,
            tenant_id=assignment.tenant_id,
            before=snap if before is not None else None,
            after=None if action == "delete" else snap,
        )


sso_sync_service: Final = SsoSyncService()
