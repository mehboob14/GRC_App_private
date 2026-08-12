"""The provider-plane role→key map and its dependency. No database, no HTTP.

The map is held in code deliberately (add-provider-plane/design.md): the
``permissions``/``roles`` tables are tenant-scoped and cannot hold a provider
grant. These tests pin the approved key set so a later edit is a visible diff.
"""

from __future__ import annotations

import uuid

import pytest

from verity.core.deps import (
    PROVIDER_ROLE_PERMISSIONS,
    PlatformAdminPrincipal,
    require_provider,
)
from verity.core.errors import PermissionDenied

TENANT_KEYS = {
    "tenants:create",
    "tenants:read",
    "tenants:update",
    "tenants:brand",
    "tenants:provision",
}


def _admin(role: str) -> PlatformAdminPrincipal:
    return PlatformAdminPrincipal(id=uuid.uuid4(), role=role, status="active")


def test_the_role_map_is_exactly_the_approved_table() -> None:
    assert set(PROVIDER_ROLE_PERMISSIONS) == {"super_admin", "onboarding", "support"}
    assert PROVIDER_ROLE_PERMISSIONS["super_admin"] == TENANT_KEYS | {"platform_admins:manage"}
    assert PROVIDER_ROLE_PERMISSIONS["onboarding"] == TENANT_KEYS
    assert PROVIDER_ROLE_PERMISSIONS["support"] == {"tenants:read"}


def test_only_super_admin_manages_platform_admins() -> None:
    assert _admin("super_admin").has("platform_admins:manage")
    assert not _admin("onboarding").has("platform_admins:manage")
    assert not _admin("support").has("platform_admins:manage")


def test_an_unknown_role_grants_nothing() -> None:
    """Deny by default: a role added to the CHECK constraint but not to the map
    holds no keys, rather than every key."""
    ghost = _admin("intern")
    assert not any(ghost.has(key) for key in TENANT_KEYS | {"platform_admins:manage"})


async def test_require_provider_returns_the_admin_when_granted() -> None:
    admin = _admin("onboarding")
    dependency = require_provider("tenants:create")
    assert await dependency(admin=admin) is admin


async def test_require_provider_refuses_a_missing_key_with_403() -> None:
    dependency = require_provider("tenants:create")
    with pytest.raises(PermissionDenied):
        await dependency(admin=_admin("support"))
