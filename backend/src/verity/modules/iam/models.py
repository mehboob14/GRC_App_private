"""Identity and access: the ten tables of openspec/changes/add-identity-and-access.

The column lists follow design.md exactly, as approved by week1-review-decisions.md
items 11-13. The shape in one sentence (ADR-0011): a person is one global ``users``
row; their place in a tenant is one ``tenant_memberships`` row; every in-tenant
reference to a person is a foreign key to the membership, never to the user.

Derived columns, approved explicitly (decision 11):

- ``credentials.last_totp_counter`` — TOTP replay protection. ``core.security``
  refuses any code at or before the stored counter, which is what closes the
  ~90-second replay window a bare TOTP check leaves open.
- ``user_identities.provider_type`` — required by ADR-0006 so the Phase 3
  federation seam can tell OIDC from SAML without a migration.

``user_identities`` is the federation seam: created, constrained, and **used by
nothing** in this change. No router, service, or repository imports it — a unit
test enforces that — so Phase 3 federates by inserting rows, not by rewriting.

``role_assignments.assignee_id`` is polymorphic with ``assignee_type`` (same
reasoning as ``audit_log.actor_id``), and ``engagement_id`` is a bare uuid with
**no FK** until the compliance module creates ``engagements``. The auditor
time-box (``valid_from`` / ``valid_until``) lives here, on the assignment,
because the window scopes the grant, not the person's existence in the tenant.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Final

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey, status_check

USER_STATUSES: Final[tuple[str, ...]] = ("active", "disabled")
USER_STATUS_ACTIVE: Final = "active"

MEMBERSHIP_STATUSES: Final[tuple[str, ...]] = ("invited", "active", "disabled")
MEMBERSHIP_STATUS_INVITED: Final = "invited"
MEMBERSHIP_STATUS_ACTIVE: Final = "active"
MEMBERSHIP_STATUS_DISABLED: Final = "disabled"

IDENTITY_PROVIDER_TYPES: Final[tuple[str, ...]] = ("oidc", "saml")

ASSIGNEE_TYPES: Final[tuple[str, ...]] = ("membership", "group")
ASSIGNEE_TYPE_MEMBERSHIP: Final = "membership"
ASSIGNEE_TYPE_GROUP: Final = "group"

ADMIN_ROLE_NAME: Final = "Admin"
"""The built-in role whose members must hold TOTP (decision 19) and whose
permission set is "every key that exists", resolved at check time (decision 13)."""


class User(UUIDPrimaryKey, Timestamped, Base):
    """A person, independent of any tenant. Email is unique globally (ADR-0011)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[str]
    status: Mapped[str] = mapped_column(default=USER_STATUS_ACTIVE)
    # Denormalised convenience flag from the ER diagram; the secret itself lives
    # on credentials, encrypted.
    mfa_enabled: Mapped[bool] = mapped_column(server_default=text("false"), default=False)
    # NULL until the work email is confirmed via the link mailed at signup; a user
    # with no verification cannot obtain a session.
    email_verified_at: Mapped[datetime | None] = mapped_column(default=None)
    # When the account holder accepted the Terms & Privacy at signup — a recorded
    # fact for a compliance product, not just a client-side checkbox.
    terms_accepted_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (status_check("users", "status", USER_STATUSES),)

    def __repr__(self) -> str:
        # No email: this string ends up in tracebacks, and an address is PII.
        return f"User(id={self.id!r}, status={self.status!r})"


class Credentials(Timestamped, Base):
    """One credential record per user. The primary key *is* the user.

    ``password_hash`` is argon2id via ``core.security``; ``mfa_secret_encrypted``
    is envelope ciphertext AAD-bound to ``credentials:<user_id>``;
    ``recovery_codes_encrypted`` holds argon2id hashes of single-use codes.
    Plaintext never reaches these columns, and none of them survives into a log,
    a response, or an audit snapshot (the deny-list redacts by name).
    """

    __tablename__ = "credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str]
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(default=None)
    recovery_codes_encrypted: Mapped[list[str] | None] = mapped_column(JSONB(), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(default=None)
    last_totp_counter: Mapped[int | None] = mapped_column(BigInteger, default=None)

    def __repr__(self) -> str:
        # Deliberately no credential columns.
        return f"Credentials(user_id={self.user_id!r})"


class UserIdentity(UUIDPrimaryKey, Timestamped, Base):
    """The federation seam (ADR-0006). Created now, used by nothing until Phase 3.

    No router, service, or repository in this module may import this class —
    ``tests/unit/test_iam_module.py`` fails the build if one does.
    """

    __tablename__ = "user_identities"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str]
    provider_type: Mapped[str]
    external_subject_id: Mapped[str]

    __table_args__ = (
        status_check("user_identities", "provider_type", IDENTITY_PROVIDER_TYPES),
        UniqueConstraint(
            "provider", "external_subject_id", name="uq_user_identities__provider_subject"
        ),
        UniqueConstraint("user_id", "provider"),
    )

    def __repr__(self) -> str:
        return f"UserIdentity(id={self.id!r}, provider={self.provider!r})"


class TenantMembership(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One person's place in one tenant — the tenant-scoped person of ADR-0011.

    ``UNIQUE (tenant_id, user_id)``: a person is in a tenant once. A second
    tenant is a second row, which is the Week 1 demo criterion made structural.
    """

    __tablename__ = "tenant_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(default=MEMBERSHIP_STATUS_INVITED)
    invited_at: Mapped[datetime | None] = mapped_column(default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(default=None)
    disabled_at: Mapped[datetime | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("tenant_memberships", "status", MEMBERSHIP_STATUSES),
        UniqueConstraint("tenant_id", "user_id"),
        Index("ix_tenant_memberships__tenant_id_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"TenantMembership(id={self.id!r}, tenant_id={self.tenant_id!r}, "
            f"status={self.status!r})"
        )


class Group(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A named set of memberships, tenant-scoped."""

    __tablename__ = "groups"

    name: Mapped[str]

    __table_args__ = (UniqueConstraint("tenant_id", "name"),)

    def __repr__(self) -> str:
        return f"Group(id={self.id!r}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class GroupMember(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A membership in a group. The member is the *membership*, never the user.

    ``tenant_id`` is denormalised onto the join (design.md): the RLS policy is a
    direct column comparison, and a cross-tenant ``(group_in_A, membership_in_B)``
    pair fails ``WITH CHECK`` before the foreign keys are even considered. The
    service additionally verifies both sides live in the caller's tenant.
    """

    __tablename__ = "group_members"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    tenant_membership_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenant_memberships.id", ondelete="CASCADE")
    )

    __table_args__ = (
        UniqueConstraint(
            "group_id", "tenant_membership_id", name="uq_group_members__group_id_membership"
        ),
        Index("ix_group_members__tenant_id_membership", "tenant_id", "tenant_membership_id"),
    )

    def __repr__(self) -> str:
        return f"GroupMember(group_id={self.group_id!r}, member={self.tenant_membership_id!r})"


class Permission(Timestamped, Base):
    """A flat ``module:action`` key. Global content, like frameworks: a tenant
    receives the key set the platform ships and composes *roles* from it."""

    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(primary_key=True)
    module: Mapped[str]
    action: Mapped[str]

    def __repr__(self) -> str:
        return f"Permission(key={self.key!r})"


class Role(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A named bundle of permission keys, tenant-scoped, built-in or custom.

    Built-in roles refuse deletion (409). The built-in Admin role carries no
    ``role_permissions`` rows at all: its grant is "every key that exists",
    resolved at check time (decision 13), so a new module's keys reach Admin
    without a data migration.
    """

    __tablename__ = "roles"

    name: Mapped[str]
    built_in: Mapped[bool] = mapped_column(server_default=text("false"), default=False)

    __table_args__ = (UniqueConstraint("tenant_id", "name"),)

    def __repr__(self) -> str:
        return f"Role(id={self.id!r}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class RolePermission(Timestamped, Base):
    """One key in one role's bundle. No ``tenant_id``: reachable only through
    ``roles``, which is tenant-scoped and RLS-protected (design.md)."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_key: Mapped[str] = mapped_column(ForeignKey("permissions.key"), primary_key=True)

    def __repr__(self) -> str:
        return f"RolePermission(role_id={self.role_id!r}, key={self.permission_key!r})"


class RoleAssignment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A role granted to a membership or a group, optionally time-boxed.

    The auditor path: ``engagement_id`` plus the window. Expired means invisible
    — the window is checked at permission-resolution time on every request, not
    by a nightly job. Uniqueness on ``(role_id, assignee_type, assignee_id,
    engagement_id)`` is enforced in the service (a duplicate is a 409); the
    design's index table deliberately carries no unique constraint here because
    ``engagement_id`` is nullable and NULLs would not collide.
    """

    __tablename__ = "role_assignments"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    assignee_type: Mapped[str]
    assignee_id: Mapped[uuid.UUID]
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    valid_from: Mapped[date | None] = mapped_column(default=None)
    valid_until: Mapped[date | None] = mapped_column(default=None)

    __table_args__ = (
        status_check("role_assignments", "assignee_type", ASSIGNEE_TYPES),
        CheckConstraint(
            "valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until",
            # conv: the ck naming convention would otherwise wrap this explicit
            # name a second time at table-attach (see db.base.status_check).
            name=conv("ck_role_assignments__window_order"),
        ),
        Index(
            "ix_role_assignments__tenant_id_assignee",
            "tenant_id",
            "assignee_type",
            "assignee_id",
        ),
        Index(
            "ix_role_assignments__tenant_id_engagement",
            "tenant_id",
            "engagement_id",
            postgresql_where=text("engagement_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"RoleAssignment(id={self.id!r}, role_id={self.role_id!r}, "
            f"assignee_type={self.assignee_type!r}, assignee_id={self.assignee_id!r})"
        )
