"""The dependency shapes Week 1 implements behind.

These assert the contract rather than behaviour: the signatures are settled now so that
implementing authentication changes nothing outside the IAM module.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable

import pytest

from verity.core.deps import (
    Principal,
    TenantContext,
    get_current_principal,
    get_tenant_context,
    require,
)


def test_a_principal_carries_the_membership_not_only_the_user() -> None:
    """ADR-0011: every in-tenant reference to a person is the membership, never the user."""
    principal = Principal(
        user_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        permissions=frozenset({"controls:read"}),
    )
    assert principal.membership_id is not None
    assert principal.has("controls:read")
    assert not principal.has("controls:edit")


def test_a_platform_admin_has_no_membership() -> None:
    """A separate population, not a tenant user with extra permissions."""
    admin = Principal(user_id=uuid.uuid4(), is_platform_admin=True)
    assert admin.membership_id is None
    assert admin.tenant_id is None


def test_a_principal_denies_by_default() -> None:
    """No implicit allow: an empty permission set grants nothing."""
    principal = Principal(user_id=uuid.uuid4())
    assert not principal.has("controls:read")


def test_tenant_context_records_impersonation() -> None:
    """An operator acting inside a tenant is a distinct, audit-logged path."""
    context = TenantContext(tenant_id=uuid.uuid4(), via_impersonation=True)
    assert context.membership_id is None
    assert context.via_impersonation


def test_a_principal_is_immutable() -> None:
    principal = Principal(user_id=uuid.uuid4())
    with pytest.raises(AttributeError):
        principal.is_platform_admin = True  # type: ignore[misc]


def test_repr_does_not_dump_every_permission() -> None:
    principal = Principal(
        user_id=uuid.uuid4(), permissions=frozenset({f"module{n}:read" for n in range(50)})
    )
    assert "module7:read" not in repr(principal)


@pytest.mark.parametrize(
    "dependency", [get_current_principal, get_tenant_context, require("controls:read")]
)
async def test_unimplemented_dependencies_fail_closed_and_say_why(
    dependency: Callable[..., Awaitable[object]],
) -> None:
    """Not a silent allow. A route wired to these refuses until Week 1 lands."""
    with pytest.raises(NotImplementedError, match="Week 1"):
        await dependency()


def test_require_names_the_permission_it_was_given() -> None:
    with pytest.raises(NotImplementedError, match="evidence:approve"):
        asyncio.run(require("evidence:approve")())
