"""Management commands, run as ``python -m verity.manage <command>``.

Commands::

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

    python -m verity.manage reset-password --email someone@example.com

Sets a new password on an existing tenant user and prints it once. For the case
where the mailed reset link cannot be used -- no SMTP configured, a mailbox
nobody can reach any more, an operator recovering their own access on a host
they control. It goes through the same ``reset_password`` the emailed link does,
so the workspace's password policy is enforced, the reset is written as a real
credential change, and **every existing session for that user is revoked**.
Writing a hash directly would skip all three.
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
from verity.seed.loader import load_all

SEED_PASSWORD_ENV: Final = "VERITY_SEED_ADMIN_PASSWORD"  # noqa: S105 — the variable's name
RESET_PASSWORD_ENV: Final = "VERITY_RESET_PASSWORD"  # noqa: S105 — the variable's name
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


_PASSWORD_GROUPS: Final[tuple[str, ...]] = (
    "ABCDEFGHJKLMNPQRSTUVWXYZ",
    "abcdefghijkmnopqrstuvwxyz",
    "23456789",
    "!@#$%^&*-_=+?",
)
"""One group per policy rule, using unambiguous characters only: no I/l/1 or
O/0, because this password is read off a terminal and typed in by hand at least
once."""

_GENERATED_PASSWORD_LENGTH: Final = 20


def _generate_password() -> str:
    """A password that provably satisfies the shipped policy.

    Built rather than sampled: ``secrets.token_urlsafe`` can return a string with
    no digit or no uppercase, and a reset that fails validation after the
    operator has already been told it succeeded is worse than no command.
    """
    alphabet = "".join(_PASSWORD_GROUPS)
    characters = [secrets.choice(group) for group in _PASSWORD_GROUPS]
    characters += [
        secrets.choice(alphabet) for _ in range(_GENERATED_PASSWORD_LENGTH - len(_PASSWORD_GROUPS))
    ]
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


async def _reset_password(email: str) -> int:
    from verity.core.security import issue_token  # noqa: PLC0415 — command-local
    from verity.modules.iam.repository import UserRepository  # noqa: PLC0415
    from verity.modules.iam.service import iam_auth_service  # noqa: PLC0415

    email_n = email.strip().lower()
    password = os.environ.get(RESET_PASSWORD_ENV) or _generate_password()
    generated = not os.environ.get(RESET_PASSWORD_ENV)

    try:
        async with provider_session_scope() as session:
            user = await UserRepository().get_by_email(session, email_n)
            if user is None:
                # Named plainly. The HTTP route is deliberately quiet about
                # whether an address exists; an operator on the host running this
                # command already has the database, so silence here would only
                # cost them an hour.
                print(f"refused: no user with email {email_n}.", file=sys.stderr)
                return 1
            if user.status != "active":
                print(
                    f"refused: {email_n} is {user.status}, not active. "
                    "Re-enable the membership first.",
                    file=sys.stderr,
                )
                return 1
            user_id = user.id

        # Mint the same token the emailed link carries, then redeem it through
        # the same service call, so this path cannot drift from that one.
        token = issue_token(subject=user_id, plane="tenant", typ="password_reset").token
        await iam_auth_service.reset_password(token=token, new_password=password)
    finally:
        await dispose_engine()

    print(f"password reset: {email_n}")
    if generated:
        print(f"new password: {password}")
        print("Store it now; it is not recoverable and is shown exactly once.")
    else:
        print(f"password taken from ${RESET_PASSWORD_ENV}.")
    print("Every existing session for this user has been revoked.")
    print("MFA is untouched — if it was enrolled, it is still required at sign-in.")
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

    reset = commands.add_parser(
        "reset-password",
        help="set a new password on an existing tenant user and print it once",
    )
    reset.add_argument("--email", required=True)

    commands.add_parser(
        "seed-content",
        help="load the shipped global content packs (frameworks, requirements, control templates)",
    )
    return parser


async def _seed_content() -> int:
    result = await load_all()
    print(result.summary())
    print("no changes — content already current." if not result.changed else "content updated.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    if arguments.command == "seed-platform-admin":
        return asyncio.run(
            _seed_platform_admin(arguments.email, arguments.full_name, arguments.role)
        )
    if arguments.command == "reset-password":
        return asyncio.run(_reset_password(arguments.email))
    if arguments.command == "seed-content":
        return asyncio.run(_seed_content())
    raise AssertionError("argparse guarantees a known command")


if __name__ == "__main__":
    raise SystemExit(main())
