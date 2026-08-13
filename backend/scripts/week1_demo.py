"""Week 1 end-to-end demo, driven through the real HTTP API.

Runs the exact scenario: create two organisations (self-service signup + admin
MFA), invite the SAME external auditor into both as a time-boxed guest, have the
auditor accept both and sign in, prove they can switch between both workspaces,
and print each tenant's audit trail.

Usage (API must be running on 127.0.0.1:8001):
    uv --directory backend run python scripts/week1_demo.py
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pyotp

BASE = "http://127.0.0.1:8001/api/v1"
RUN = uuid.uuid4().hex[:8]
# The access window is resolved in UTC on every request; anchor the demo to UTC
# today so "from now" is unambiguously active regardless of the server timezone.
WINDOW_FROM = datetime.now(UTC).date().isoformat()
WINDOW_UNTIL = (datetime.now(UTC).date() + timedelta(days=30)).isoformat()
PW_ADMIN = "orbit-mango-quartz-42"
PW_AUDITOR = "delta-crimson-otter-77"


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def ok(msg: str) -> None:
    print(f"  [ok] {msg}")


def post(client: httpx.Client, path: str, *, token: str | None = None, **kw: object) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.post(f"{BASE}{path}", headers=headers, **kw)
    if r.status_code >= 400:
        sys.exit(f"POST {path} -> {r.status_code}: {r.text}")
    return r.json() if r.content else {}


def get(client: httpx.Client, path: str, *, token: str | None = None) -> object:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = client.get(f"{BASE}{path}", headers=headers)
    if r.status_code >= 400:
        sys.exit(f"GET {path} -> {r.status_code}: {r.text}")
    return r.json()


def verify_email(client: httpx.Client, email: str) -> dict:
    """Confirm the work email the way the mailed link would. Signup sends a real
    email; this script runs in the backend venv, so it mints the same
    ``email_verify`` token the link carries (looking up the user id directly)
    rather than reading an inbox."""
    import asyncio

    import asyncpg

    from verity.core.config import get_settings
    from verity.core.security import issue_token

    async def _user_id() -> object:
        dsn = get_settings().database.url.replace("+asyncpg", "")
        conn = await asyncpg.connect(dsn)
        try:
            return await conn.fetchval(
                "SELECT id FROM users WHERE email = $1", email.strip().lower()
            )
        finally:
            await conn.close()

    token = issue_token(subject=asyncio.run(_user_id()), plane="tenant", typ="email_verify").token
    return post(client, "/auth/verify-email", json={"token": token})


def create_org(client: httpx.Client, company: str, email: str) -> dict:
    """Self-service signup + email verification + TOTP enrollment. Returns the
    admin's session state."""
    res = post(
        client,
        "/auth/signup",
        json={
            "company_name": company,
            "full_name": "Founding Admin",
            "email": email,
            "password": PW_ADMIN,
            "accept_terms": True,
        },
    )
    assert res["status"] == "email_verification_required", res
    ok(f"signed up '{company}' — a verification email was sent to {email}")
    verified = verify_email(client, email)
    assert verified["status"] == "mfa_enrollment_required", verified
    ok("email verified — admin must now enroll MFA (Admin role)")
    challenge = verified["challenge_token"]

    started = post(client, "/auth/mfa/enroll", json={"challenge_token": challenge})
    secret = started["secret"]
    code = pyotp.TOTP(secret).now()
    confirmed = post(client, "/auth/mfa/confirm", json={"challenge_token": challenge, "code": code})
    assert confirmed["status"] == "authenticated", confirmed
    ok(f"MFA enrolled + first session issued ({len(confirmed['recovery_codes'])} recovery codes)")
    return {
        "token": confirmed["access_token"],
        "tenant_id": confirmed["principal"]["tenant_id"],
        "tenant_name": confirmed["principal"]["tenant_name"],
        "email": email,
        "secret": secret,
    }


def auditor_role_id(client: httpx.Client, token: str) -> str:
    roles = get(client, "/roles", token=token)
    auditor = next(r for r in roles if r["name"] == "Auditor")  # type: ignore[index]
    return auditor["id"]  # type: ignore[index,return-value]


def main() -> None:
    client = httpx.Client(timeout=30.0)
    auditor_email = f"dana.auditor+{RUN}@external.example"

    step("1. Create organisation A (self-service, admin MFA)")
    a = create_org(client, f"Alpha Compliance {RUN}", f"founder+a{RUN}@alpha.example")
    print(f"       tenant A = {a['tenant_name']}  ({a['tenant_id']})")

    step("2. Create organisation B (self-service, admin MFA)")
    b = create_org(client, f"Bravo Assurance {RUN}", f"founder+b{RUN}@bravo.example")
    print(f"       tenant B = {b['tenant_name']}  ({b['tenant_id']})")

    step("3. Admin A invites the auditor as a time-boxed GUEST (no IdP, platform-native)")
    role_a = auditor_role_id(client, a["token"])
    inv_a = post(
        client,
        "/members/invite",
        token=a["token"],
        json={
            "email": auditor_email,
            "full_name": "Dana Auditor",
            "role_id": role_a,
            "valid_from": WINDOW_FROM,
            "valid_until": WINDOW_UNTIL,
        },
    )
    ok(f"invited into A as Auditor, access window {WINDOW_FROM} -> {WINDOW_UNTIL}")
    ok(f"one-time accept link returned to inviter: {inv_a['accept_url'][:70]}...")

    step("4. Admin B invites the SAME auditor (guest in a second organisation)")
    role_b = auditor_role_id(client, b["token"])
    inv_b = post(
        client,
        "/members/invite",
        token=b["token"],
        json={
            "email": auditor_email,
            "full_name": "Dana Auditor",
            "role_id": role_b,
            "valid_from": WINDOW_FROM,
            "valid_until": WINDOW_UNTIL,
        },
    )
    ok("invited into B as Auditor — same person, second tenant, one global identity")

    step("5. Auditor accepts BOTH invitations")
    acc_a = post(
        client,
        "/auth/invitations/accept",
        json={"token": inv_a["invite_token"], "full_name": "Dana Auditor", "password": PW_AUDITOR},
    )
    ok(f"accepted A ({acc_a['tenant_name']}) — new user: set name + password once")
    acc_b = post(client, "/auth/invitations/accept", json={"token": inv_b["invite_token"]})
    ok(f"accepted B ({acc_b['tenant_name']}) — existing user: token alone, no new password")

    step("6. Auditor signs in — one credential, two workspaces")
    login = post(client, "/auth/login", json={"email": auditor_email, "password": PW_AUDITOR})
    assert login["status"] == "select_workspace", login
    names = sorted(w["tenant_name"] for w in login["workspaces"])
    ok(f"login resolved to select_workspace across {len(login['workspaces'])}: {names}")
    ok("auditor is not an Admin → no MFA required (MFA is admins-only on the tenant plane)")

    by_name = {w["tenant_name"]: w for w in login["workspaces"]}
    wa, wb = by_name[a["tenant_name"]], by_name[b["tenant_name"]]

    sess_a = post(
        client,
        "/auth/workspaces/select",
        json={"selection_token": login["selection_token"], "membership_id": wa["membership_id"]},
    )
    assert sess_a["status"] == "authenticated"
    ok(f"entered workspace A as {sess_a['principal']['role_names']}")

    workspaces = get(client, "/auth/workspaces", token=sess_a["access_token"])
    ok(
        f"GET /auth/workspaces from A session lists both: "
        f"{sorted(w['tenant_name'] for w in workspaces)}"
    )  # type: ignore[index]

    sess_b = post(
        client,
        "/auth/workspaces/switch",
        token=sess_a["access_token"],
        json={"membership_id": wb["membership_id"]},
    )
    assert sess_b["status"] == "authenticated"
    ok("switched to workspace B — new session bound to the B membership")

    step("7. Audit trail — every action is recorded, per tenant stream")
    for label, admin in (("A", a), ("B", b)):
        page = get(client, "/audit-log?limit=100", token=admin["token"])
        items = page["items"] if isinstance(page, dict) else page  # type: ignore[index]
        print(f"\n  Tenant {label} ({admin['tenant_name']}) — {len(items)} events:")
        for e in reversed(items):  # oldest first
            actor = e.get("actor_type", "?")
            print(f"    - {e['action']:<10} {e['object_type']:<18} actor={actor}")

    print(f"\n[PASS] Week 1 demo path verified end-to-end against the live API (run {RUN}).")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"       ({time.time() - t0:.1f}s)")
