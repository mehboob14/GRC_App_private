"""Management commands, run as ``python -m verity.manage <command>``.

One command so far::

    python -m verity.manage seed-platform-admin \
        --email ops@example.com --name "Ops Admin" --role super_admin

Creates the **first** platform admin and refuses to run once any exists — after
that, admins are managed through the provider panel by a ``super_admin`` holding
``platform_admins:manage``. The initial password comes from the
``VERITY_SEED_ADMIN_PASSWORD`` environment variable when set, and is otherwise
generated and printed exactly once. It is deliberately printed, never logged: the
logging pipeline redacts anything password-shaped, and stdout of an interactive
seed run is the one place the operator can receive it. MFA enrollment is forced on
first login — the admin is created unenrolled, and the login route answers
``mfa_enroll`` until a TOTP secret is confirmed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from collections.abc import Sequence
from typing import Final

from verity.core.db import dispose_engine, provider_session_scope
from verity.core.security import hash_password
from verity.modules.audit.service import AuditService, System, audit_service
from verity.modules.tenancy.models import (
    PLATFORM_ADMIN_ROLES,
    PLATFORM_ADMIN_STATUS_ACTIVE,
    PlatformAdmin,
)
from verity.modules.tenancy.repository import PlatformAdminRepository

SEED_PASSWORD_ENV: Final = "VERITY_SEED_ADMIN_PASSWORD"  # noqa: S105 — the variable's name
_GENERATED_PASSWORD_BYTES: Final = 24


async def _seed_platform_admin(email: str, full_name: str, role: str) -> int:
    password = os.environ.get(SEED_PASSWORD_ENV) or None
    generated = password is None
    if password is None:
        password = secrets.token_urlsafe(_GENERATED_PASSWORD_BYTES)

    repository = PlatformAdminRepository()
    try:
        async with provider_session_scope() as session:
            if await repository.count(session) > 0:
                print(
                    "refused: platform_admins is not empty. Further admins are "
                    "managed through the provider panel (platform_admins:manage).",
                    file=sys.stderr,
                )
                return 1
            admin = PlatformAdmin(
                email=email.strip().lower(),
                full_name=full_name,
                role=role,
                status=PLATFORM_ADMIN_STATUS_ACTIVE,
                mfa_enabled=False,
                password_hash=hash_password(password),
            )
            await repository.add(session, admin)
            # Seeding is a state change like any other; the snapshot redacts every
            # credential-shaped column by name.
            await audit_service.record(
                session,
                action="create",
                object_type="platform_admin",
                object_id=admin.id,
                actor=System(),
                tenant_id=None,
                after=AuditService.snapshot(admin),
            )
    finally:
        await dispose_engine()

    print(f"platform admin created: {email.strip().lower()} (role={role})")
    if generated:
        print(f"one-time initial password: {password}")
        print("Store it now; it is not recoverable and is shown exactly once.")
    else:
        print(f"password taken from ${SEED_PASSWORD_ENV}.")
    print("TOTP enrollment is forced on first login.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m verity.manage")
    commands = parser.add_subparsers(dest="command", required=True)

    seed = commands.add_parser(
        "seed-platform-admin",
        help="create the first platform admin (refuses once any admin exists)",
    )
    seed.add_argument("--email", required=True)
    seed.add_argument("--name", required=True, dest="full_name")
    seed.add_argument("--role", choices=PLATFORM_ADMIN_ROLES, default="super_admin")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    if arguments.command == "seed-platform-admin":
        return asyncio.run(
            _seed_platform_admin(arguments.email, arguments.full_name, arguments.role)
        )
    raise AssertionError("argparse guarantees a known command")


if __name__ == "__main__":
    raise SystemExit(main())
