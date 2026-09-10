"""The ``audit_log`` table — append-only, dual-plane, and deliberately FK-free.

Three deviations from the usual table shape, each approved in
openspec/changes/week1-review-decisions.md (decision 1):

- ``tenant_id`` is **the stream the event belongs to, not the actor's tenant**, is
  nullable (NULL = provider plane), and carries no foreign key. Every FK action is
  incompatible with append-only — a teardown cascade is a ``DELETE`` the trigger
  refuses — and the record of a tenant being torn down is precisely the record that
  must outlive the tenant.
- ``actor_type``/``actor_id`` is a polymorphic pair with no FK: the id points at
  ``tenant_memberships``, ``platform_admins``, or nothing, depending on the type,
  and Postgres has no constraint for that.
- ``occurred_at`` alone, no ``created_at``/``updated_at``: an ``updated_at`` on a
  table that refuses ``UPDATE`` could only ever repeat ``occurred_at``.

The ORM listeners at the bottom are the third layer of append-only enforcement,
behind the revoked grant and the database trigger (add-audit-trail/design.md): they
catch a mutation in a unit test with no database, while the developer is looking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Final, Literal, NoReturn, get_args

from sqlalchemy import CheckConstraint, Index, event, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import conv

from verity.db.base import Base, UUIDPrimaryKey, status_check, tenant_index

AuditAction = Literal["create", "update", "delete", "transition", "approve"]
"""The five verbs the ER design enumerates. Authentication rides them rather than
adding a sixth: login is ``create`` on ``object_type='session'``, sign-out ``delete``
on the same (week1-review-decisions.md, decision 2)."""

AUDIT_ACTIONS: Final[tuple[str, ...]] = get_args(AuditAction)

ActorType = Literal["membership", "platform_admin", "system", "vendor_contact"]

ACTOR_TYPES: Final[tuple[str, ...]] = get_args(ActorType)

ACTOR_TYPE_MEMBERSHIP: Final = "membership"
ACTOR_TYPE_PLATFORM_ADMIN: Final = "platform_admin"
ACTOR_TYPE_SYSTEM: Final = "system"
# A person at a third party, acting through the vendor questionnaire portal.
# They hold a token rather than a session and have no membership, which is the
# whole reason the actor is a polymorphic pair rather than one foreign key.
ACTOR_TYPE_VENDOR_CONTACT: Final = "vendor_contact"


class AuditLogAppendOnlyError(RuntimeError):
    """Application code tried to mutate an audit row.

    A defect, not a domain condition — deliberately not a ``VerityError``, exactly
    like ``TenantContextError``: it surfaces as a generic 500 rather than as a code
    a client could branch on.
    """


class AuditLog(UUIDPrimaryKey, Base):
    """One recorded state change. Written once, never touched again."""

    __tablename__ = "audit_log"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    """The stream, not the actor. NULL = provider plane. No FK — see the module
    docstring."""

    actor_type: Mapped[str]
    actor_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    """NULL exactly when ``actor_type = 'system'`` — the paired CHECK below makes
    the discriminator load-bearing rather than decoration."""

    action: Mapped[str]
    object_type: Mapped[str]
    object_id: Mapped[uuid.UUID]
    before: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    after: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        status_check("audit_log", "actor_type", ACTOR_TYPES),
        status_check("audit_log", "action", AUDIT_ACTIONS),
        CheckConstraint(
            "(actor_type = 'system') = (actor_id IS NULL)",
            # conv: the ck naming convention would otherwise wrap this explicit name
            # a second time at table-attach (see db.base.status_check).
            name=conv("ck_audit_log__system_actor_has_no_actor_id"),
        ),
        tenant_index("audit_log", "object_type", "object_id"),
        tenant_index("audit_log", "actor_id"),
    )


# The default list, newest first, and the keyset cursor. DESC needs the mapped
# column, which only exists once the class is configured, so it lives here rather
# than in __table_args__ with the other two.
Index(
    "ix_audit_log__tenant_id_occurred_at",
    AuditLog.tenant_id,
    AuditLog.occurred_at.desc(),
)


_APPEND_ONLY_MESSAGE: Final = (
    "audit_log is append-only: {operation} is not permitted (docs/conventions/database.md)"
)


@event.listens_for(AuditLog, "before_update")
def refuse_orm_update(_mapper: object, _connection: object, _target: object) -> NoReturn:
    raise AuditLogAppendOnlyError(_APPEND_ONLY_MESSAGE.format(operation="UPDATE"))


@event.listens_for(AuditLog, "before_delete")
def refuse_orm_delete(_mapper: object, _connection: object, _target: object) -> NoReturn:
    raise AuditLogAppendOnlyError(_APPEND_ONLY_MESSAGE.format(operation="DELETE"))
