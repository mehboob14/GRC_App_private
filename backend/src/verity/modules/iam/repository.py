"""Data access for identity and access. No business rules, no commits.

Every tenant-scoped query filters ``tenant_id`` explicitly — RLS is the second
wall, not the mechanism. The deliberate exceptions are the **identity-plane**
lookups (marked below): resolving a person's memberships across tenants at
login time cannot know a tenant to filter by, so those queries filter on the
global ``user_id`` / membership primary key instead and rely on the caller
running inside ``core.db.provider_session_scope`` — the identity-resolution
policies on these tables are SELECT-only, keyed on ``app.provider_plane``
(see the iam migration).

``user_identities`` is deliberately absent from this file: the federation seam
is written by nothing until Phase 3 (design.md, "The federation seam").
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.iam.models import (
    ADMIN_ROLE_NAME,
    ASSIGNEE_TYPE_MEMBERSHIP,
    MEMBERSHIP_STATUS_ACTIVE,
    Credentials,
    Group,
    GroupMember,
    Permission,
    Role,
    RoleAssignment,
    RolePermission,
    TenantMembership,
    User,
)


class UserRepository:
    """Global identity rows: ``users`` and ``credentials`` carry no tenant."""

    async def add(self, session: AsyncSession, user: User) -> None:
        session.add(user)
        await session.flush([user])

    async def get(self, session: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await session.get(User, user_id)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_many(self, session: AsyncSession, user_ids: Sequence[uuid.UUID]) -> list[User]:
        if not user_ids:
            return []
        result = await session.execute(select(User).where(User.id.in_(user_ids)))
        return list(result.scalars())

    async def add_credentials(self, session: AsyncSession, credentials: Credentials) -> None:
        session.add(credentials)
        await session.flush([credentials])

    async def get_credentials(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> Credentials | None:
        return await session.get(Credentials, user_id)


class MembershipRepository:
    async def add(self, session: AsyncSession, membership: TenantMembership) -> None:
        session.add(membership)
        await session.flush([membership])

    async def get(self, session: AsyncSession, membership_id: uuid.UUID) -> TenantMembership | None:
        """Identity-plane lookup by primary key — no tenant filter, because the
        caller (an auth flow resolving a token subject) does not know the tenant
        until this row answers. Runs under the identity-resolution SELECT policy."""
        return await session.get(TenantMembership, membership_id)

    async def get_for_tenant(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> TenantMembership | None:
        result = await session.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.id == membership_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tenant_user(
        self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> TenantMembership | None:
        result = await session.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, session: AsyncSession, user_id: uuid.UUID
    ) -> list[TenantMembership]:
        """Identity-plane lookup: every membership of one person, across tenants.
        This is the login-time resolution ADR-0011 exists for."""
        result = await session.execute(
            select(TenantMembership)
            .where(TenantMembership.user_id == user_id)
            .order_by(TenantMembership.id)
        )
        return list(result.scalars())

    async def list_for_tenant(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[TenantMembership]:
        result = await session.execute(
            select(TenantMembership)
            .where(TenantMembership.tenant_id == tenant_id)
            .order_by(TenantMembership.id)
        )
        return list(result.scalars())


class GroupRepository:
    async def add(self, session: AsyncSession, group: Group) -> None:
        session.add(group)
        await session.flush([group])

    async def get_for_tenant(
        self, session: AsyncSession, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> Group | None:
        result = await session.execute(
            select(Group).where(Group.tenant_id == tenant_id, Group.id == group_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self, session: AsyncSession, tenant_id: uuid.UUID, name: str
    ) -> Group | None:
        result = await session.execute(
            select(Group).where(Group.tenant_id == tenant_id, Group.name == name)
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[Group]:
        result = await session.execute(
            select(Group).where(Group.tenant_id == tenant_id).order_by(Group.name)
        )
        return list(result.scalars())

    async def add_member(self, session: AsyncSession, member: GroupMember) -> None:
        session.add(member)
        await session.flush([member])

    async def get_member(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> GroupMember | None:
        result = await session.execute(
            select(GroupMember).where(
                GroupMember.tenant_id == tenant_id,
                GroupMember.group_id == group_id,
                GroupMember.tenant_membership_id == membership_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[GroupMember]:
        result = await session.execute(
            select(GroupMember).where(GroupMember.tenant_id == tenant_id)
        )
        return list(result.scalars())

    async def group_ids_for_membership(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> list[uuid.UUID]:
        result = await session.execute(
            select(GroupMember.group_id).where(
                GroupMember.tenant_id == tenant_id,
                GroupMember.tenant_membership_id == membership_id,
            )
        )
        return list(result.scalars())

    async def group_names_by_membership(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, list[str]]:
        result = await session.execute(
            select(GroupMember.tenant_membership_id, Group.name)
            .join(Group, Group.id == GroupMember.group_id)
            .where(GroupMember.tenant_id == tenant_id, Group.tenant_id == tenant_id)
            .order_by(Group.name)
        )
        names: dict[uuid.UUID, list[str]] = {}
        for membership_id, name in result.all():
            names.setdefault(membership_id, []).append(name)
        return names


class RoleRepository:
    """Roles, their permission bundles, and their assignments."""

    async def add(self, session: AsyncSession, role: Role) -> None:
        session.add(role)
        await session.flush([role])

    async def delete(self, session: AsyncSession, role: Role) -> None:
        await session.delete(role)
        await session.flush()

    async def get_for_tenant(
        self, session: AsyncSession, tenant_id: uuid.UUID, role_id: uuid.UUID
    ) -> Role | None:
        result = await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self, session: AsyncSession, tenant_id: uuid.UUID, name: str
    ) -> Role | None:
        result = await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[Role]:
        result = await session.execute(
            select(Role).where(Role.tenant_id == tenant_id).order_by(Role.name)
        )
        return list(result.scalars())

    async def get_many(
        self, session: AsyncSession, tenant_id: uuid.UUID, role_ids: Sequence[uuid.UUID]
    ) -> list[Role]:
        if not role_ids:
            return []
        result = await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.id.in_(role_ids))
        )
        return list(result.scalars())

    # -- permission bundles ---------------------------------------------------

    async def add_permission_keys(
        self, session: AsyncSession, role_id: uuid.UUID, keys: Iterable[str]
    ) -> None:
        rows = [RolePermission(role_id=role_id, permission_key=key) for key in keys]
        session.add_all(rows)
        await session.flush(rows)

    async def permission_keys_by_role(
        self, session: AsyncSession, role_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[str]]:
        if not role_ids:
            return {}
        result = await session.execute(
            select(RolePermission.role_id, RolePermission.permission_key)
            .where(RolePermission.role_id.in_(role_ids))
            .order_by(RolePermission.permission_key)
        )
        keys: dict[uuid.UUID, list[str]] = {}
        for role_id, key in result.all():
            keys.setdefault(role_id, []).append(key)
        return keys

    async def existing_permission_keys(
        self, session: AsyncSession, keys: Sequence[str] | None = None
    ) -> set[str]:
        """All shipped keys, or the subset of ``keys`` that actually exists."""
        statement = select(Permission.key)
        if keys is not None:
            if not keys:
                return set()
            statement = statement.where(Permission.key.in_(keys))
        result = await session.execute(statement)
        return set(result.scalars())

    # -- assignments ------------------------------------------------------------

    async def add_assignment(self, session: AsyncSession, assignment: RoleAssignment) -> None:
        session.add(assignment)
        await session.flush([assignment])

    async def delete_assignment(self, session: AsyncSession, assignment: RoleAssignment) -> None:
        await session.delete(assignment)
        await session.flush()

    async def get_assignment(
        self, session: AsyncSession, tenant_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> RoleAssignment | None:
        result = await session.execute(
            select(RoleAssignment).where(
                RoleAssignment.tenant_id == tenant_id, RoleAssignment.id == assignment_id
            )
        )
        return result.scalar_one_or_none()

    async def find_assignment(  # noqa: PLR0913 — the assignment's idempotency key, whole
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        role_id: uuid.UUID,
        assignee_type: str,
        assignee_id: uuid.UUID,
        engagement_id: uuid.UUID | None,
    ) -> RoleAssignment | None:
        """The duplicate check: idempotency key of an assignment (design.md)."""
        engagement_predicate = (
            RoleAssignment.engagement_id.is_(None)
            if engagement_id is None
            else RoleAssignment.engagement_id == engagement_id
        )
        result = await session.execute(
            select(RoleAssignment).where(
                RoleAssignment.tenant_id == tenant_id,
                RoleAssignment.role_id == role_id,
                RoleAssignment.assignee_type == assignee_type,
                RoleAssignment.assignee_id == assignee_id,
                engagement_predicate,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_assignees(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        membership_id: uuid.UUID,
        group_ids: Sequence[uuid.UUID],
    ) -> list[RoleAssignment]:
        """Every assignment that could grant this membership anything: direct
        rows plus rows targeting any of its groups. Window filtering is the
        caller's job — the same rows also answer "what is expired"."""
        direct = (RoleAssignment.assignee_type == "membership") & (
            RoleAssignment.assignee_id == membership_id
        )
        predicate = direct
        if group_ids:
            predicate = direct | (
                (RoleAssignment.assignee_type == "group")
                & (RoleAssignment.assignee_id.in_(group_ids))
            )
        result = await session.execute(
            select(RoleAssignment).where(RoleAssignment.tenant_id == tenant_id, predicate)
        )
        return list(result.scalars())

    async def list_direct_for_membership(
        self, session: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
    ) -> list[RoleAssignment]:
        result = await session.execute(
            select(RoleAssignment).where(
                RoleAssignment.tenant_id == tenant_id,
                RoleAssignment.assignee_type == ASSIGNEE_TYPE_MEMBERSHIP,
                RoleAssignment.assignee_id == membership_id,
            )
        )
        return list(result.scalars())

    async def list_for_role(
        self, session: AsyncSession, tenant_id: uuid.UUID, role_id: uuid.UUID
    ) -> list[RoleAssignment]:
        result = await session.execute(
            select(RoleAssignment).where(
                RoleAssignment.tenant_id == tenant_id, RoleAssignment.role_id == role_id
            )
        )
        return list(result.scalars())

    async def assignment_counts(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        result = await session.execute(
            select(RoleAssignment.role_id).where(RoleAssignment.tenant_id == tenant_id)
        )
        counts: dict[uuid.UUID, int] = {}
        for role_id in result.scalars():
            counts[role_id] = counts.get(role_id, 0) + 1
        return counts

    async def direct_role_names_by_membership(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict[uuid.UUID, list[str]]:
        """Display names for the members list: direct assignments only."""
        result = await session.execute(
            select(RoleAssignment.assignee_id, Role.name)
            .join(Role, Role.id == RoleAssignment.role_id)
            .where(
                RoleAssignment.tenant_id == tenant_id,
                RoleAssignment.assignee_type == ASSIGNEE_TYPE_MEMBERSHIP,
                Role.tenant_id == tenant_id,
            )
            .order_by(Role.name)
        )
        names: dict[uuid.UUID, list[str]] = {}
        for membership_id, name in result.all():
            names.setdefault(membership_id, []).append(name)
        return names

    # -- provisioning gates ------------------------------------------------------

    async def admin_membership_exists(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        require_active: bool,
    ) -> bool:
        """Whether the tenant has a membership holding the built-in Admin role —
        the two provisioning gates of week1-review-decisions.md, decision 10."""
        membership_predicate = TenantMembership.id == RoleAssignment.assignee_id
        if require_active:
            membership_predicate = membership_predicate & (
                TenantMembership.status == MEMBERSHIP_STATUS_ACTIVE
            )
        statement = select(
            exists().where(
                RoleAssignment.tenant_id == tenant_id,
                RoleAssignment.assignee_type == ASSIGNEE_TYPE_MEMBERSHIP,
                Role.id == RoleAssignment.role_id,
                Role.tenant_id == tenant_id,
                Role.built_in.is_(True),
                Role.name == ADMIN_ROLE_NAME,
                TenantMembership.tenant_id == tenant_id,
                membership_predicate,
            )
        )
        return bool((await session.execute(statement)).scalar_one())
